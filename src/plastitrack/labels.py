"""Rule-based (weak) labels from Open Food Facts packaging fields.

Open Food Facts rarely records packaging *weights*, but it often records packaging
*materials and shapes* (packaging_tags / packaging_text). We turn those into two labels:

  plastic_level : none / low / medium / high
  plastic_type  : none / PET / HDPE / PP / film / mixed_other

The ML model later learns to predict these labels from product name, brand and
category alone (no packaging fields), because order emails never mention packaging.
"""
import re

# --- keyword lists (matched against lowercase tags + free text) -------------
PET_KW = ["pet", "pete", "rpet", "polyethylene-terephthalate", "polyethylene terephthalate"]
HDPE_KW = ["hdpe", "pe-hd", "high-density-polyethylene", "high density polyethylene"]
PP_KW = ["polypropylene", "pp-5", "5-pp"]
FILM_KW = ["ldpe", "pe-ld", "low-density-polyethylene", "film", "plastic-bag", "plastic bag",
           "wrap", "sachet", "pouch", "flow-pack", "flowpack", "shrink", "cellophane"]
OTHER_PLASTIC_KW = ["plastic", "plastique", "plastico", "plástico", "kunststoff", "plastica",
                    "polystyrene", "pvc", "blister", "styrofoam", "polyethylene", "pe-"]
# minor plastic in a mostly non-plastic pack (e.g. juice carton = paper + plastic layer)
COMPOSITE_KW = ["tetra", "brick", "composite", "multilayer", "aseptic", "gable-top"]
NONPLASTIC_KW = ["glass", "verre", "vidrio", "cardboard", "carton", "paper", "papier", "carton",
                 "metal", "can", "aluminium", "aluminum", "tin", "steel", "boite", "box",
                 "jar", "wood", "cork"]
# shapes that are (almost always) plastic when no material is given
PLASTIC_SHAPES = {"tray": "mixed_other", "tub": "PP", "pot": "PP", "bag": "film", "sachet": "film",
                  "pouch": "film", "blister": "mixed_other", "film": "film", "wrapper": "film"}
# signals of heavy over-packaging
HEAVY_KW = ["individually wrapped", "individually-wrapped", "multipack", "multi-pack",
            "blister", "clamshell"]

# all plastic-looking keywords, used to count plastic components
PLASTIC_TAG_KW = PET_KW + HDPE_KW + PP_KW + FILM_KW + OTHER_PLASTIC_KW + list(PLASTIC_SHAPES)

PLASTIC_LEVELS = ["none", "low", "medium", "high"]
PLASTIC_TYPES = ["none", "PET", "HDPE", "PP", "film", "mixed_other"]


def _split_tags(tags):
    """'en:plastic,en:bottle' -> ['plastic', 'bottle'] (language prefix removed)."""
    if not isinstance(tags, str) or not tags.strip():
        return []
    return [t.split(":", 1)[-1].strip().lower() for t in tags.split(",") if t.strip()]


_PATTERNS = {}


def _has(text, keywords):
    """Whole-word-ish match so 'pet' doesn't hit 'petfood' and 'can' doesn't hit 'canada'.
    One compiled regex per keyword list (cached) keeps this fast on millions of rows."""
    key = id(keywords)
    if key not in _PATTERNS:
        alts = "|".join(re.escape(k) for k in keywords)
        _PATTERNS[key] = re.compile(rf"(?<![a-z])(?:{alts})(?![a-z])")
    return _PATTERNS[key].search(text) is not None


def label_packaging(packaging_tags, packaging_text=""):
    """Return (plastic_level, plastic_type) or (None, None) if packaging is unknown."""
    tags = _split_tags(packaging_tags)
    free = packaging_text.lower() if isinstance(packaging_text, str) else ""
    all_text = " ".join(tags) + " " + free
    if not all_text.strip():
        return None, None

    # 1) which specific plastic types are mentioned?
    types = set()
    if _has(all_text, PET_KW):
        types.add("PET")
    if _has(all_text, HDPE_KW):
        types.add("HDPE")
    if _has(all_text, PP_KW) or re.search(r"(?<![a-z])pp(?![a-z])", all_text):
        types.add("PP")
    if _has(all_text, FILM_KW):
        types.add("film")
    generic_plastic = _has(all_text, OTHER_PLASTIC_KW)

    # 2) generic "plastic" + a shape -> infer a type (plastic bottle is usually PET, etc.)
    if generic_plastic and not types:
        if "bottle" in all_text or "bouteille" in all_text:
            types.add("PET")
        elif "jug" in all_text or "milk" in all_text:
            types.add("HDPE")
        else:
            for shape, ptype in PLASTIC_SHAPES.items():
                if re.search(rf"(?<![a-z]){shape}", all_text):
                    types.add(ptype)
                    break

    has_plastic = bool(types) or generic_plastic
    composite = _has(all_text, COMPOSITE_KW)
    nonplastic = _has(all_text, NONPLASTIC_KW)

    # number of plastic components = tags that look plastic
    n_plastic_parts = sum(1 for t in tags if _has(t, PLASTIC_TAG_KW))

    # 3) plastic type
    if not has_plastic and not composite:
        if not nonplastic:
            return None, None          # unknown material -> don't use this row
        return "none", "none"
    if not has_plastic and composite:
        ptype = "mixed_other"          # e.g. Tetra Pak: paperboard + PE + aluminium
    elif len(types) == 1:
        ptype = next(iter(types))
    else:
        ptype = "mixed_other"          # several plastics, or plastic of unknown kind

    # 4) plastic level
    heavy = _has(all_text, HEAVY_KW) or ("tray" in all_text and "film" in all_text)
    if heavy or n_plastic_parts >= 3:
        level = "high"
    elif nonplastic or (composite and not types):
        level = "low"                  # mostly glass/paper/metal with a plastic cap, window or lining
    else:
        level = "medium"               # plastic is the main pack (bottle, tub, bag)
    return level, ptype


if __name__ == "__main__":
    # quick self-test with realistic tag strings
    examples = [
        ("en:plastic,en:bottle", ""),
        ("en:glass,en:jar,en:metal-lid", ""),
        ("en:cardboard,en:box,en:plastic-film", ""),
        ("en:tray,en:film,en:plastic", ""),
        ("en:tetra-pak", ""),
        ("en:pp-5-polypropylene,en:tub", ""),
        ("en:can", ""),
        ("", "sachet plastique"),
        ("en:bag", ""),
        ("", ""),
    ]
    for tags, txt in examples:
        print(f"{tags or txt!r:45} -> {label_packaging(tags, txt)}")
