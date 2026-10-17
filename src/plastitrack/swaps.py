"""Lower-plastic swap rules + template text.

The *choice* of swap is rule-based (predictable, explainable). The *wording* can be
personalized by the local LLM (see llm.py); `template_tip()` is the always-works fallback.
"""
import re

# (regex on product name, swap suggestion, estimated plastic reduction 0-1)
PRODUCT_SWAPS = [
    (r"\bwater\b.*(pack|bottle)|bottled water|purified water|spring water",
     "a filter pitcher plus a reusable bottle", 0.95),
    (r"gatorade|sports drink|thirst quencher", "powdered drink mix in a carton, mixed in a reusable bottle", 0.85),
    (r"soda|cola", "a home carbonation maker or larger cans", 0.6),
    (r"yogurt|yoghurt", "one large 32 oz tub instead of single-serve cups", 0.6),
    (r"\bmilk\b", "milk in returnable glass bottles or paper cartons", 0.7),
    (r"laundry|detergent|pods", "laundry detergent sheets in a cardboard box", 0.95),
    (r"body wash|shower gel", "bar soap in a paper wrapper", 0.9),
    (r"shampoo(?! bar)", "a shampoo bar", 0.95),
    (r"conditioner", "a conditioner bar", 0.95),
    (r"toothpaste", "toothpaste tablets in a glass jar", 0.9),
    (r"toothbrush", "bamboo toothbrushes", 0.8),
    (r"razor", "a metal safety razor with paper-wrapped blades", 0.95),
    (r"deodorant", "deodorant in a paper push-up tube", 0.9),
    (r"chips|crisps", "a larger family-size bag (less film per gram) or bulk snacks", 0.4),
    (r"strawberr|berries|blueberr|raspberr", "loose berries in a cardboard punnet or from a farmers market", 0.8),
    (r"salad|spring mix|lettuce|spinach", "whole heads of lettuce instead of clamshell salad", 0.85),
    (r"bacon|chicken|beef|pork|meat|sausage", "the butcher counter with paper wrapping", 0.7),
    (r"trash bag|garbage bag", "bags made from recycled plastic or compostable bags", 0.5),
    (r"ziploc|storage bag|sandwich bag|zip bag", "reusable silicone storage bags", 0.9),
    (r"baby wipes", "reusable cloth wipes", 0.85),
    (r"wipes", "reusable microfiber cloths with a spray bottle refill", 0.9),
    (r"dish soap|dishwashing", "a solid dish soap bar or a refill station", 0.8),
    (r"paper towel", "reusable cloth towels (and paper-wrapped rolls when needed)", 0.7),
    (r"ice cream", "ice cream in paperboard pints", 0.5),
    (r"granola bar|protein bar|snack bar", "homemade bars or a bulk box of unwrapped bars", 0.6),
    (r"cable|charger", "one multi-device cable and brands with plastic-free packaging", 0.5),
    (r"batter", "rechargeable batteries", 0.9),
]

# fallback by category group
CATEGORY_SWAPS = {
    "beverages": ("drinks in glass or aluminum, or concentrates", 0.6),
    "dairy": ("larger containers or glass-bottle dairy", 0.5),
    "snacks_sweets": ("bulk or larger packs", 0.4),
    "personal_care": ("solid (bar) versions of this product", 0.8),
    "household": ("concentrated refills or plastic-free versions", 0.6),
    "electronics": ("brands with plastic-free packaging, and fewer, longer-lasting items", 0.4),
    "fresh_produce": ("loose produce", 0.8),
    "meat_fish": ("the butcher or fish counter with paper wrapping", 0.6),
    "frozen": ("fresh or bulk alternatives", 0.4),
}
DEFAULT_SWAP = ("a larger size or a refillable version", 0.4)


def suggest_swap(product, category):
    """Return (swap text, reduction fraction) for a product."""
    name = product.lower()
    for pattern, swap, reduction in PRODUCT_SWAPS:
        if re.search(pattern, name):
            return swap, reduction
    return CATEGORY_SWAPS.get(category, DEFAULT_SWAP)


def short_name(product):
    """'Dove Deep Moisture Body Wash, 22 fl oz' -> 'Dove Deep Moisture Body Wash'."""
    return re.split(r",|\(", product)[0].strip()


def template_tip(product, times, grams, swap, reduction):
    """Deterministic fallback text (always available, instant)."""
    saved = grams * reduction
    return (f"You bought {short_name(product)} {times} times recently, about {grams:,.0f} g of plastic. "
            f"Switching to {swap} could avoid roughly {saved:,.0f} g.")
