"""Train the PlastiTrack predictive models on LinuxONE.

Two targets:  plastic_level (none/low/medium/high)  and  plastic_type (none/PET/HDPE/PP/film/mixed_other)
Two models per target: TF-IDF + Logistic Regression (baseline) and TF-IDF + XGBoost.
The model with the best macro-F1 on the held-out test set is saved to models/.

Run inside the lab container, from the project root:
    python scripts/train_model.py                 # full run
    python scripts/train_model.py --rows 20000    # quick smoke test
"""
import argparse
import json
import os
import platform
import sys
import time

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.feature_selection import SelectKBest, chi2  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,  # noqa: E402
                             confusion_matrix, f1_score)
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import LabelEncoder  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from plastitrack.features import frame_to_text, make_featurizer  # noqa: E402
from plastitrack.labels import PLASTIC_LEVELS, PLASTIC_TYPES  # noqa: E402

TARGETS = {"plastic_level": PLASTIC_LEVELS, "plastic_type": PLASTIC_TYPES}


def plot_confusion(y_true, y_pred, labels, title, path):
    cm = confusion_matrix(y_true, y_pred, labels=labels, normalize="true")
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ConfusionMatrixDisplay(cm, display_labels=labels).plot(ax=ax, cmap="Greens", values_format=".2f",
                                                          colorbar=False)
    ax.set_title(title)
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed/products_labeled.csv")
    ap.add_argument("--rows", type=int, default=0, help="use only N rows (0 = all)")
    ap.add_argument("--xgb-rounds", type=int, default=300)
    ap.add_argument("--xgb-features", type=int, default=3000)
    args = ap.parse_args()

    print(f"Platform: {platform.machine()} | Python {platform.python_version()} | {os.cpu_count()} CPUs")
    df = pd.read_csv(args.data, dtype=str, keep_default_na=False)
    if args.rows:
        df = df.sample(args.rows, random_state=42)
    X_text = frame_to_text(df)
    print(f"Rows: {len(df):,}")

    os.makedirs("models", exist_ok=True)
    os.makedirs("reports/figures", exist_ok=True)
    all_metrics = {}

    for target, classes in TARGETS.items():
        print(f"\n================ target: {target} ================")
        y = df[target].values
        X_tr, X_te, y_tr, y_te = train_test_split(X_text, y, test_size=0.2, random_state=42, stratify=y)

        t0 = time.time()
        featurizer = make_featurizer()
        F_tr = featurizer.fit_transform(X_tr)
        F_te = featurizer.transform(X_te)
        print(f"features: {F_tr.shape[1]:,} columns  ({time.time() - t0:.0f}s)")

        enc = LabelEncoder().fit(classes)
        results = {}

        # --- 1) baseline: logistic regression -------------------------------------
        t0 = time.time()
        lr = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")
        lr.fit(F_tr, y_tr)
        pred = lr.predict(F_te)
        results["logreg"] = (lr, pred, time.time() - t0)

        # --- 2) XGBoost (hist trees, runs natively on s390x) ---------------------------
        # Trees are slow on 80k sparse columns, so keep the 3,000 most informative (chi-squared).
        t0 = time.time()
        selector = SelectKBest(chi2, k=min(args.xgb_features, F_tr.shape[1])).fit(F_tr, y_tr)
        S_tr = selector.transform(F_tr)
        X_fit, X_val, y_fit, y_val = train_test_split(S_tr, y_tr, test_size=0.1, random_state=0, stratify=y_tr)
        # inverse-frequency sample weights to balance classes (like class_weight="balanced")
        counts = pd.Series(y_fit).value_counts()
        w = np.array([len(y_fit) / (len(counts) * counts[c]) for c in y_fit])
        xgb = XGBClassifier(n_estimators=args.xgb_rounds, max_depth=6, learning_rate=0.15,
                            subsample=0.8, colsample_bytree=0.5, tree_method="hist",
                            n_jobs=os.cpu_count(), eval_metric="mlogloss", early_stopping_rounds=30)
        xgb.fit(X_fit, enc.transform(y_fit), sample_weight=w,
                eval_set=[(X_val, enc.transform(y_val))], verbose=50)
        xgb_pipe = Pipeline([("select", selector), ("xgb", xgb)])   # already fitted steps
        pred = enc.inverse_transform(xgb_pipe.predict(F_te))
        results["xgboost"] = (xgb_pipe, pred, time.time() - t0)

        # --- evaluate ----------------------------------------------------------------
        metrics = {}
        for name, (model, pred, secs) in results.items():
            m = {"accuracy": round(accuracy_score(y_te, pred), 4),
                 "macro_f1": round(f1_score(y_te, pred, average="macro"), 4),
                 "weighted_f1": round(f1_score(y_te, pred, average="weighted"), 4),
                 "train_seconds": round(secs, 1)}
            metrics[name] = m
            print(f"\n--- {name}: acc={m['accuracy']}  macroF1={m['macro_f1']}  "
                  f"weightedF1={m['weighted_f1']}  ({secs:.0f}s)")
            print(classification_report(y_te, pred, digits=3, zero_division=0))
            plot_confusion(y_te, pred, classes, f"{target} — {name} (LinuxONE s390x)",
                           f"reports/figures/cm_{target}_{name}.png")

        best = max(metrics, key=lambda k: metrics[k]["macro_f1"])
        print(f">>> best model for {target}: {best}")
        joblib.dump({"featurizer": featurizer, "model": results[best][0], "kind": best,
                     "classes": classes, "encoder": enc if best == "xgboost" else None},
                    f"models/{target}.joblib")
        metrics["best"] = best
        all_metrics[target] = metrics

    all_metrics["platform"] = {"machine": platform.machine(), "byteorder": sys.byteorder,
                               "python": platform.python_version(), "rows": len(df)}
    with open("reports/metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2)
    print("\nSaved models/*.joblib, reports/metrics.json, reports/figures/cm_*.png")


if __name__ == "__main__":
    main()
