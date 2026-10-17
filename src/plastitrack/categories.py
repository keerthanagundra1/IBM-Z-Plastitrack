"""Map free-text categories / product names to a small set of category groups.

Used for (a) dashboard breakdowns and (b) the grams-per-item lookup table.
First matching group wins, so more specific groups come first.
"""
import re

CATEGORY_GROUPS = [
    ("baby", ["baby", "infant", "diaper", "nappy", "nappies", "toddler"]),
    ("pet", ["pet food", "dog food", "dog treat", "cat food", "cat litter", "pet "]),
    ("electronics", ["electronic", "cable", "charger", "headphone", "earbud", "battery", "batteries",
                     "usb", "phone case", "adapter", "mouse", "keyboard", "led bulb", "speaker"]),
    ("household", ["detergent", "laundry", "dish", "cleaner", "cleaning", "bleach", "trash bag",
                   "garbage bag", "paper towel", "toilet paper", "sponge", "aluminum foil", "foil",
                   "plastic wrap", "zip bag", "storage bag", "household", "air freshener", "wipes"]),
    ("personal_care", ["shampoo", "conditioner", "soap", "body wash", "shower gel", "toothpaste",
                       "toothbrush", "deodorant", "lotion", "face cream", "hand cream", "cosmetic", "beauty", "makeup",
                       "razor", "sunscreen", "hygiene", "face wash", "mouthwash", "hair"]),
    ("frozen", ["frozen", "ice cream", "ice-cream"]),
    ("snacks_sweets", ["snack", "chip", "crisp", "cookie", "biscuit", "candy", "chocolate",
                       "confection", "sweet", "cracker", "protein bar", "granola bar", "cereal bar",
                       "snack bar", "popcorn", "gum", "nuts"]),
    ("beverages", ["beverage", "drink", "water", "soda", "juice", "coffee", "tea", "beer", "wine",
                   "cola", "sparkling", "kombucha", "energy drink", "plant-based milk", "smoothie",
                   "gatorade", "thirst quencher", "sports drink", "lemonade"]),
    ("dairy", ["dairy", "milk", "yogurt", "yoghurt", "cheese", "butter", "cream", "egg"]),
    ("meat_fish", ["meat", "chicken", "beef", "pork", "fish", "seafood", "sausage", "ham", "bacon",
                   "turkey", "salmon", "tuna"]),
    ("sauces_condiments", ["sauce", "condiment", "ketchup", "mayonnaise", "dressing", "spread",
                           "jam", "preserves", "honey", "oil", "vinegar", "spice", "seasoning", "salt"]),
    ("fresh_produce", ["fruit", "vegetable", "salad", "produce", "berries", "apple", "banana",
                       "tomato", "lettuce", "spinach", "strawberr", "blueberr", "raspberr"]),
    ("bakery", ["bread", "bakery", "bun", "bagel", "tortilla", "cake", "pastry", "muffin"]),
    ("pantry", ["cereal", "pasta", "rice", "grain", "flour", "sugar", "legume", "bean", "soup",
                "canned", "noodle", "oat", "breakfast"]),
]
CATEGORY_NAMES = [name for name, _ in CATEGORY_GROUPS] + ["other"]

_COMPILED = [
    (name, re.compile(r"(?<![a-z])(?:" + "|".join(re.escape(k) for k in kws) + r")"))
    for name, kws in CATEGORY_GROUPS
]


def category_group(*texts):
    """Return the first matching group for the given text fields, else 'other'."""
    blob = " ".join(t.lower() for t in texts if isinstance(t, str))
    for name, pattern in _COMPILED:
        if pattern.search(blob):
            return name
    return "other"


if __name__ == "__main__":
    for t in ["Beverages, Waters, Spring waters", "Dairies, Yogurts", "Tide Pods Laundry Detergent",
              "Head & Shoulders Shampoo", "Anker USB-C Charger", "Doritos Nacho Cheese Chips"]:
        print(f"{t:40} -> {category_group(t)}")
