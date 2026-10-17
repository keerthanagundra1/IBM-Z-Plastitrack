"""Predict plastic level + type for product titles with the models trained on LinuxONE.

Hybrid: the ML model predicts from the title; if the title itself names the packaging
("Glass Jar", "Cans", "Clamshell", "Shampoo Bar"...), that explicit hint wins.
Every prediction records its `source` ("model" or "title hint") for transparency.
"""
import os
import re

import joblib

from .categories import category_group
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

    def _predict_target(self, target, texts):
        bundle = self.models[target]
        feats = bundle["featurizer"].transform(texts)
        model = bundle["model"]
        proba = model.predict_proba(feats)
        idx = proba.argmax(axis=1)
        if bundle["kind"] == "xgboost":
            labels = bundle["encoder"].inverse_transform(idx)
        else:
            labels = model.classes_[idx]
        return list(labels), proba.max(axis=1)

    def predict(self, products, quantities=None):
        """products: list of titles -> list of dicts with level, type, confidence, category, grams, source."""
        quantities = quantities or [1] * len(products)
        texts = [build_text(p) for p in products]
        levels, lconf = self._predict_target("plastic_level", texts)
        types, tconf = self._predict_target("plastic_type", texts)
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
            out.append({"plastic_level": level, "plastic_type": ptype,
                        "confidence": round(float(min(lconf[i], tconf[i])), 2) if source == "model" else 1.0,
                        "category": cat, "source": source,
                        "plastic_g": estimate_grams(product, cat, level, quantities[i])})
        return out
