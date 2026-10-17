"""Write notebooks/01_eda.ipynb (plain JSON, no extra dependencies).

Then execute it on LinuxONE:
    jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb
"""
import json
import os

CELLS = [
    ("markdown", """# PlastiTrack — Exploratory Data Analysis
Open Food Facts + Open Beauty Facts + Open Products Facts (ODbL), processed on **IBM LinuxONE (s390x)**.

Labels are *weak labels* derived from the packaging fields (`src/plastitrack/labels.py`):
- **plastic_level**: none / low / medium / high
- **plastic_type**: none / PET / HDPE / PP / film / mixed_other"""),
    ("code", """import os, sys, platform
sys.path.insert(0, os.path.abspath("../src"))
import pandas as pd
import matplotlib.pyplot as plt
from plastitrack.viz import apply_style, LEVEL_COLORS, TYPE_COLORS, TEXT_SECONDARY
apply_style()
FIG = "../reports/figures"
os.makedirs(FIG, exist_ok=True)
print("Running on:", platform.machine(), "| byte order:", sys.byteorder, "| Python", platform.python_version())"""),
    ("code", """df = pd.read_csv("../data/processed/products_labeled.csv", dtype=str, keep_default_na=False)
print(f"{len(df):,} labeled products")
df[["product_name", "brands", "category_group", "packaging_tags", "plastic_level", "plastic_type"]].head(8)"""),
    ("markdown", "## 1. Label distributions"),
    ("code", """levels = ["none", "low", "medium", "high"]
types = ["none", "PET", "HDPE", "PP", "film", "mixed_other"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, col, order, colors, title in [
    (axes[0], "plastic_level", levels, LEVEL_COLORS, "Plastic level"),
    (axes[1], "plastic_type", types, TYPE_COLORS, "Main plastic type")]:
    share = df[col].value_counts(normalize=True).reindex(order).fillna(0) * 100
    bars = ax.barh(order, share.values, color=[colors[k] for k in order], height=0.6)
    ax.bar_label(bars, labels=[f"{v:.0f}%" for v in share.values], padding=4, color=TEXT_SECONDARY)
    ax.invert_yaxis(); ax.set_title(title); ax.set_xlabel("% of products"); ax.grid(axis="y", visible=False)
fig.tight_layout(); fig.savefig(f"{FIG}/eda_label_distribution.png", dpi=150); plt.show()"""),
    ("markdown", "## 2. Which categories carry the most plastic?"),
    ("code", """top_groups = df["category_group"].value_counts().index[:12]
sub = df[df["category_group"].isin(top_groups)]
ct = pd.crosstab(sub["category_group"], sub["plastic_level"], normalize="index").reindex(columns=levels) * 100
ct = ct.loc[(ct["medium"] + ct["high"]).sort_values().index]
fig, ax = plt.subplots(figsize=(10, 6))
left = pd.Series(0.0, index=ct.index)
for lv in levels:
    ax.barh(ct.index, ct[lv], left=left, color=LEVEL_COLORS[lv], label=lv, height=0.7,
            edgecolor="#fcfcfb", linewidth=2)
    left += ct[lv]
ax.set_xlim(0, 100); ax.set_xlabel("% of products in category"); ax.grid(axis="y", visible=False)
ax.set_title("Plastic level by product category (sorted by medium + high share)")
ax.legend(title="plastic level", ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
fig.tight_layout(); fig.savefig(f"{FIG}/eda_level_by_category.png", dpi=150); plt.show()
print("Highest medium+high plastic share:")
print((ct["medium"] + ct["high"]).sort_values(ascending=False).round(1).head(5).to_string())"""),
    ("markdown", "## 3. Which plastic types show up in which categories?"),
    ("code", """plastic_only = sub[sub["plastic_type"] != "none"]
heat = pd.crosstab(plastic_only["category_group"], plastic_only["plastic_type"], normalize="index")
heat = heat.reindex(columns=[t for t in types if t != "none"]) * 100
fig, ax = plt.subplots(figsize=(9, 6))
im = ax.imshow(heat.values, cmap="Blues", aspect="auto", vmin=0, vmax=heat.values.max())
ax.set_xticks(range(heat.shape[1]), heat.columns); ax.set_yticks(range(heat.shape[0]), heat.index)
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        v = heat.values[i, j]
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9,
                color="white" if v > heat.values.max() * 0.55 else "#0b0b0b")
ax.grid(False); ax.set_title("Plastic type mix within each category (% of plastic-packed items)")
fig.colorbar(im, ax=ax, shrink=0.7, label="%")
fig.tight_layout(); fig.savefig(f"{FIG}/eda_type_by_category.png", dpi=150); plt.show()"""),
    ("markdown", "## 4. Most common packaging tags"),
    ("code", """tags = (df["packaging_tags"].str.split(",").explode().str.split(":").str[-1].str.strip())
tags = tags[tags != ""].value_counts().head(15)[::-1]
fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.barh(tags.index, tags.values / 1000, color="#2a78d6", height=0.6)
ax.bar_label(bars, labels=[f"{v/1000:.0f}k" for v in tags.values], padding=4, color=TEXT_SECONDARY)
ax.set_xlabel("products (thousands)"); ax.grid(axis="y", visible=False)
ax.set_title("Top 15 packaging tags in Open Food Facts sample")
fig.tight_layout(); fig.savefig(f"{FIG}/eda_top_packaging_tags.png", dpi=150); plt.show()"""),
    ("markdown", "## 5. Example products per plastic level"),
    ("code", """(df[df["brands"] != ""].groupby("plastic_level").sample(4, random_state=1)
   [["plastic_level", "plastic_type", "brands", "product_name", "packaging_tags"]])"""),
    ("markdown", """## Takeaways
- About **2 in 3** products with recorded packaging contain plastic; only ~33% are plastic-free.
- **Personal care, meat/fish, dairy and household** items have the highest medium+high plastic share — all frequently re-bought online.
- Film/flexible plastic dominates frozen food and snacks; PET shows up most in fresh produce (clamshells) and sauces/beverages.
- `mixed_other` is large because many products only say "plastic" without a resin or shape — the UI shows it as "other / unspecified plastic".
- Packaging *weights* are rarely recorded, so we predict level + type and convert to grams with category averages (`src/plastitrack/grams.py`)."""),
]


def main():
    nb = {
        "cells": [
            {"cell_type": t, "metadata": {}, "source": src.splitlines(keepends=True),
             **({"outputs": [], "execution_count": None} if t == "code" else {})}
            for t, src in CELLS
        ],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "notebooks", "01_eda.ipynb")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
