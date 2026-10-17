"""Predict plastic level + type for product titles with the models trained on LinuxONE.

Hybrid: the ML model predicts from the title; if the title itself names the packaging
("Glass Jar", "Cans", "Clamshell", "Shampoo Bar"...), that explicit hint wins.
Every prediction records its `source` ("model" or "title hint") for transparency.
"""
import os
import re

import joblib

from .categories import CATEGORY_NAMES, category_group
from .features import build_text
from .grams import estimate_grams

MODEL_DIR = os.environ.get("PLASTITRACK_MODELS", os.path.join(os.path.dirname(__file__), "..", "..", "models"))

# explicit packaging words in a product title -> (level, type)
TITLE_HINTS = [
    (r"shampoo bar|soap bar|bar soap|conditioner bar|bamboo", ("none", "none")),
    (r"glass (jar|bottle)", ("none", "none")),
    (r"paper ?bag|cardboard|carton\b", ("low", "mixed_other")),
    (r"\bcans?\b", ("low", "mixed_other")),            # aluminum can: thin plastic lining
    (r"clamshell", ("medium", "PET")),
    (r"(trash|garbage|storage|zip|sandwich|freezer) bags?|ziploc", ("high", "film")),  # product IS plastic
    (r"individually wrapped|single[- ]serve|k-cups?|pods\b", ("high", "mixed_other")),
    (r"disposable razor|toothbrush", ("medium", "PP")),       # the product itself is plastic
    (r"wipes", ("medium", "film")),                          # plastic tub/pouch + polyester-blend wipes
]

# Our training data (Open Food/Beauty/Products Facts) has almost no electronics, so the model
# is out of its depth there. Use a transparent category default instead of a confident guess.
CATEGORY_DEFAULTS = {"electronics": ("medium", "mixed_other")}


class PlastiPredictor:
    def __init__(self, model_dir=MODEL_DIR):
        self.models = {t: joblib.load(os.path.join(model_dir, f"{t}.joblib"))
                       for t in ("plastic_level", "plastic_type")}
        self.feature_names = {t: self._feature_names(b["featurizer"]) for t, b in self.models.items()}

    @staticmethod
    def _feature_names(featurizer):
        """Readable name for every column of the FeatureUnion (words | chars | structured)."""
        names = []
        for name, trans in featurizer.transformer_list:
            if name == "words":
                names += [f"'{w}'" for w in trans.get_feature_names_out()]
            elif name == "chars":
                names += [None] * len(trans.get_feature_names_out())   # char n-grams: not shown to users
            else:
                names += ["multi-pack size", "container size", "multi-pack"] + \
                         [f"category: {g}" for g in CATEGORY_NAMES]
        return names

    def explain(self, target, x_row, label, k=3):
        """Top-k features pushing one (already featurized, CSR) row toward `label`.
        Logistic regression contribution = feature value x class weight."""
        bundle = self.models[target]
        model = bundle["model"]
        if bundle["kind"] != "logreg":
            return []
        weights = model.coef_[list(model.classes_).index(label)]
        names = self.feature_names[target]
        pairs = [(names[j], v * weights[j]) for j, v in zip(x_row.indices, x_row.data)]
        pairs = sorted((p for p in pairs if p[0] and p[1] > 0), key=lambda p: -p[1])
        return [n for n, _ in pairs[:k]]

    def _predict_target(self, target, texts):
        bundle = self.models[target]
        feats = bundle["featurizer"].transform(texts)
        model = bundle["model"]
        proba = model.predict_proba(feats)
        feats = feats.tocsr()
        idx = proba.argmax(axis=1)
        if bundle["kind"] == "xgboost":
            labels = bundle["encoder"].inverse_transform(idx)
        else:
            labels = model.classes_[idx]
        return list(labels), proba.max(axis=1), feats

    def predict(self, products, quantities=None):
        """products: list of titles -> list of dicts with level, type, confidence, category, grams, source."""
        quantities = quantities or [1] * len(products)
        texts = [build_text(p) for p in products]
        levels, lconf, lfeats = self._predict_target("plastic_level", texts)   # featurize once per batch
        types, tconf, _ = self._predict_target("plastic_type", texts)
        out = []
        for i, product in enumerate(products):
            level, ptype, source = levels[i], types[i], "model"
            for pattern, (h_level, h_type) in TITLE_HINTS:
                if re.search(pattern, product, re.I):
                    level, ptype, source = h_level, h_type, "title hint"
                    break
            cat = category_group(product)
            if source == "model" and cat in CATEGORY_DEFAULTS:
                (level, ptype), source = CATEGORY_DEFAULTS[cat], "category default"
            if level == "none":
                ptype = "none"                       # keep the two labels consistent
            elif ptype == "none":
                ptype = "mixed_other"
            if source == "model":
                why = self.explain("plastic_level", lfeats[i], level)
                why = f"model signals: {', '.join(why)}" if why else "model"
            elif source == "title hint":
                why = "packaging named in title: " + re.search(pattern, product, re.I).group(0)
            else:
                why = f"default for {cat} (outside training data)"
            out.append({"why": why, "plastic_level": level, "plastic_type": ptype,
                        "confidence": round(float(min(lconf[i], tconf[i])), 2) if source == "model" else 1.0,
                        "category": cat, "source": source,
                        "plastic_g": estimate_grams(product, cat, level, quantities[i])})
        return out
