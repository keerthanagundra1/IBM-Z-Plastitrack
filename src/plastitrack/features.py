"""Feature building shared by training (Open Food Facts rows) and inference (email line items).

Only uses information an order email actually contains: product title (incl. brand),
and size / pack-count text. No packaging fields -> no label leakage.
"""
import re

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from .categories import CATEGORY_NAMES, category_group

# unit -> multiplier to ml (liquids) or g (solids); we treat 1 ml ~ 1 g for size buckets
_UNITS = {"ml": 1, "cl": 10, "dl": 100, "l": 1000, "litre": 1000, "liter": 1000,
          "g": 1, "gr": 1, "kg": 1000, "mg": 0.001,
          "fl oz": 29.57, "floz": 29.57, "oz": 28.35, "lb": 453.6, "lbs": 453.6, "gal": 3785, "gallon": 3785}
_SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(fl\.?\s?oz|floz|ml|cl|dl|litre|liter|l|kg|mg|gr|g|oz|lbs|lb|gallon|gal)\b",
                      re.I)
_PACK_RE = re.compile(r"(?:pack of|set of|case of)\s*(\d+)|(\d+)\s*(?:x|×)\s*\d|(\d+)\s*[- ]?(?:pack|pk|ct|count|pcs|pieces)\b",
                      re.I)


def parse_quantity(text):
    """'Water, 16.9 Fl Oz (Pack of 24)' -> (pack_count=24, unit_size=500.0)."""
    text = text if isinstance(text, str) else ""
    size = 0.0
    m = _SIZE_RE.search(text)
    if m:
        unit = re.sub(r"[.\s]", " ", m.group(2).lower()).replace("  ", " ").strip()
        unit = "fl oz" if unit.replace(" ", "") == "floz" else unit
        size = float(m.group(1).replace(",", ".")) * _UNITS.get(unit, 1)
    pack = 1
    p = _PACK_RE.search(text)
    if p:
        pack = int(next(g for g in p.groups() if g))
    return min(pack, 500), min(size, 50_000)


def build_text(product_name, brands="", quantity=""):
    """Single text field the model reads: brand + title + size."""
    parts = [s for s in (brands, product_name, quantity) if isinstance(s, str) and s.strip()]
    return " ".join(parts).lower()


class StructuredFeatures(BaseEstimator, TransformerMixin):
    """Numeric features from the text: pack count, unit size (log), name-based category one-hot."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = []
        for t in X:
            pack, size = parse_quantity(t)
            group = category_group(t)
            onehot = [1.0 if group == g else 0.0 for g in CATEGORY_NAMES]
            rows.append([np.log1p(pack), np.log1p(size), float(pack > 1)] + onehot)
        return sparse.csr_matrix(np.array(rows, dtype=np.float32))


def make_featurizer():
    """TF-IDF on words + character n-grams (robust to typos/brand spellings) + structured features."""
    return FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=40_000,
                                  sublinear_tf=True, strip_accents="unicode")),
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=5,
                                  max_features=40_000, sublinear_tf=True, strip_accents="unicode")),
        ("struct", StructuredFeatures()),
    ])


def frame_to_text(df: pd.DataFrame):
    """Open Food Facts rows -> list of model input strings."""
    return [build_text(n, b, q) for n, b, q in zip(df["product_name"], df["brands"], df["quantity"])]
