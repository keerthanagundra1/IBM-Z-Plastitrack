"""Convert a predicted plastic level into estimated grams of plastic.

Open Food Facts rarely has packaging weights, so we use transparent category averages:
  packaging g  = typical plastic for ONE package of that category (at "medium" level)
                 x level multiplier x size factor x number of packages
  product g    = for items that ARE plastic (trash bags, razors, wipes): pieces x grams per piece
  line total   = (packaging g + product g) x quantity ordered

Typical weights are rounded, public ballpark figures for common packs
(e.g. 500 ml PET water bottle ~10 g, 1 gal HDPE milk jug ~60 g, shampoo bottle ~25 g).
They are estimates for awareness, not lab measurements.
"""
import re

from .features import parse_quantity

# category -> (grams of plastic for a typical package at "medium", typical package size in ml or g)
TYPICAL = {
    "beverages": (10, 500), "dairy": (12, 500), "snacks_sweets": (6, 200), "meat_fish": (15, 500),
    "fresh_produce": (15, 450), "frozen": (8, 500), "bakery": (6, 500), "sauces_condiments": (20, 500),
    "pantry": (8, 500), "personal_care": (25, 400), "household": (40, 1000), "electronics": (30, 0),
    "baby": (20, 0), "pet": (20, 1000), "other": (15, 0),
}
LEVEL_MULTIPLIER = {"none": 0.0, "low": 0.25, "medium": 1.0, "high": 1.6}

# products that are themselves (mostly) plastic: grams of plastic per piece
PLASTIC_PIECES = [
    (r"trash bag|garbage bag|bin bag", 8.0),
    (r"storage bag|zip ?bag|ziploc|sandwich bag|freezer bag", 4.0),
    (r"disposable razor", 8.0),
    (r"toothbrush", 15.0),
    (r"baby wipes", 0.5),
    (r"wipes", 1.0),
    (r"\bstraws?\b", 0.5),
    (r"\bcups?\b.*(plastic|disposable)|plastic cups?", 5.0),
]

_PACKS = re.compile(r"(?:pack|set|case) of\s*(\d+)|(\d+)\s*[- ]?(?:pack|pk)\b|(\d+)\s*(?:x|×)\s*\d", re.I)
_PIECES = re.compile(r"(\d+)\s*(?:ct|count|pcs|pieces|bags|rolls)\b", re.I)


def count_packs_and_pieces(product):
    """'Wipes, 75 ct (Pack of 3)' -> (3 packages, 75 pieces per package)."""
    m = _PACKS.search(product)
    packs = int(next(g for g in m.groups() if g)) if m else 1
    p = _PIECES.search(product)
    pieces = int(p.group(1)) if p else 1
    return min(packs, 100), min(pieces, 1000)


def estimate_grams(product, category, level, quantity=1):
    """Estimated plastic grams for one order line."""
    base, ref_size = TYPICAL.get(category, TYPICAL["other"])
    _, size = parse_quantity(product)
    packs, pieces = count_packs_and_pieces(product)
    size_factor = 1.0
    if size and ref_size:
        # bigger containers use more plastic, but less per ml (scale with exponent < 1)
        size_factor = min(max((size / ref_size) ** 0.6, 0.3), 4.0)
    packaging = base * LEVEL_MULTIPLIER.get(level, 1.0) * size_factor * packs
    product_plastic = 0.0
    for pattern, g_per_piece in PLASTIC_PIECES:
        if re.search(pattern, product, re.I):
            product_plastic = g_per_piece * pieces * packs
            break
    return round((packaging + product_plastic) * max(int(quantity), 1), 1)
