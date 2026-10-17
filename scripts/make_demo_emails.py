"""Generate synthetic order-confirmation emails for the demo (demo_emails/*.eml).

Three fictional stores, each with its own email layout:
  RiverMart Online  (marketplace style)   SuperValu Mart (big-box style)   Northstar Goods (department style)
All personal details are fake (example.com, 555 phone numbers, made-up addresses).
Orders span Aug-Oct 2026 and include repeat purchases so the alerts have something to find.
"""
import os
import random
from datetime import datetime, timedelta

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "demo_emails")

CUSTOMER = {"name": "Jordan Rivera", "first": "Jordan", "email": "jordan.rivera@example.com",
            "street": "1428 Elm Street Apt 3B", "city": "Springfield, IL 62704", "phone": "(555) 014-2290"}

# product -> unit price
P = {
    "water": ("Pure Life Purified Water, 16.9 Fl Oz (Pack of 24)", 4.98),
    "yogurt": ("Chobani Greek Yogurt Variety Pack, 5.3 oz Cups (Pack of 12)", 13.99),
    "milk": ("SuperValu Select Whole Milk, 1 gal", 3.48),
    "chips": ("Lay's Classic Potato Chips Party Size, 13 oz", 5.49),
    "berries": ("Driscoll's Strawberries, 1 lb Clamshell", 3.99),
    "bacon": ("Oscar Mayer Classic Uncured Bacon, 16 oz", 6.99),
    "pasta": ("Barilla Spaghetti Pasta, 16 oz Box", 1.79),
    "ketchup": ("Heinz Tomato Ketchup, 32 oz Bottle", 3.79),
    "cola": ("Coca-Cola Soda, 12 fl oz Cans (Pack of 12)", 7.49),
    "granola": ("Nature Valley Crunchy Granola Bars, 12 ct", 4.29),
    "chicken": ("Tyson Boneless Skinless Chicken Breasts, 2.5 lb", 12.99),
    "icecream": ("Ben & Jerry's Chocolate Fudge Brownie Ice Cream, 16 oz", 5.99),
    "jam": ("Bonne Maman Strawberry Preserves, 13 oz Glass Jar", 4.99),
    "oats": ("Quaker Old Fashioned Oats, 42 oz Canister", 5.49),
    "salad": ("Organic Spring Mix Salad, 5 oz Clamshell", 3.99),
    "gatorade": ("Gatorade Thirst Quencher, 20 fl oz Bottles (Pack of 8)", 8.99),
    "tide": ("Tide PODS Laundry Detergent, 42 ct", 13.97),
    "towels": ("Bounty Paper Towels, 6 Double Rolls", 15.99),
    "dawn": ("Dawn Ultra Dish Soap, 19.4 fl oz", 3.99),
    "trashbags": ("Glad Tall Kitchen Trash Bags, 13 Gallon, 80 ct", 14.99),
    "ziploc": ("Ziploc Storage Bags, Gallon, 38 ct", 5.49),
    "wipes": ("Clorox Disinfecting Wipes, 75 ct (Pack of 3)", 12.49),
    "bodywash": ("Dove Deep Moisture Body Wash, 22 fl oz", 8.99),
    "shampoo": ("Head & Shoulders Classic Clean Shampoo, 13.5 fl oz", 7.99),
    "toothpaste": ("Colgate Total Toothpaste, 4.8 oz (Pack of 2)", 7.49),
    "toothbrush": ("Oral-B Toothbrushes Medium, 6 ct", 9.99),
    "razors": ("Gillette Disposable Razors, 12 ct", 11.99),
    "shampoobar": ("Ethique Shampoo Bar, 3.88 oz", 15.99),
    "deodorant": ("Native Deodorant, 2.65 oz", 12.99),
    "cable": ("Anker USB-C Charging Cable, 6 ft (2-Pack)", 12.99),
    "batteries": ("Duracell AA Batteries, 20 ct", 16.99),
    "earbuds": ("JBL Wireless Earbuds with Charging Case", 49.99),
    "mouse": ("Logitech M185 Wireless Mouse", 14.99),
    "babywipes": ("Pampers Sensitive Baby Wipes, 8 Flip-Top Packs (576 ct)", 17.99),
}

# (store, date, [(product key, qty), ...])
ORDERS = [
    ("rivermart", "2026-08-03", [("water", 2), ("tide", 1), ("cable", 1)]),
    ("supervalu", "2026-08-07", [("milk", 1), ("yogurt", 1), ("berries", 2), ("bacon", 1), ("chips", 1)]),
    ("northstar", "2026-08-12", [("bodywash", 1), ("toothpaste", 1), ("razors", 1)]),
    ("rivermart", "2026-08-18", [("water", 2), ("gatorade", 1), ("ziploc", 1)]),
    ("supervalu", "2026-08-21", [("milk", 1), ("chicken", 1), ("salad", 1), ("pasta", 2), ("ketchup", 1)]),
    ("northstar", "2026-08-27", [("trashbags", 1), ("dawn", 1), ("towels", 1)]),
    ("rivermart", "2026-09-01", [("water", 2), ("batteries", 1), ("granola", 2)]),
    ("supervalu", "2026-09-04", [("yogurt", 1), ("milk", 1), ("berries", 1), ("icecream", 2)]),
    ("rivermart", "2026-09-09", [("earbuds", 1), ("shampoo", 1)]),
    ("northstar", "2026-09-13", [("babywipes", 1), ("wipes", 1), ("toothbrush", 1)]),
    ("supervalu", "2026-09-17", [("cola", 2), ("chips", 2), ("salad", 1), ("jam", 1)]),
    ("rivermart", "2026-09-22", [("water", 2), ("tide", 1), ("gatorade", 1)]),
    ("northstar", "2026-09-26", [("bodywash", 1), ("deodorant", 1), ("dawn", 1)]),
    ("supervalu", "2026-10-01", [("milk", 1), ("yogurt", 1), ("chicken", 1), ("oats", 1)]),
    ("rivermart", "2026-10-04", [("water", 2), ("mouse", 1), ("ziploc", 1)]),
    ("northstar", "2026-10-07", [("shampoobar", 1), ("toothpaste", 1), ("trashbags", 1)]),
    ("supervalu", "2026-10-10", [("berries", 2), ("bacon", 1), ("salad", 1), ("granola", 1), ("cola", 1)]),
    ("rivermart", "2026-10-13", [("water", 2), ("gatorade", 1), ("wipes", 1)]),
    ("supervalu", "2026-10-15", [("milk", 1), ("yogurt", 1), ("icecream", 1), ("chips", 1)]),
    ("northstar", "2026-10-16", [("bodywash", 1), ("razors", 1), ("towels", 1)]),
]


def money(x):
    return f"${x:,.2f}"


def rivermart(date, items, rng):
    order_no = f"112-{rng.randint(1000000, 9999999)}-{rng.randint(1000000, 9999999)}"
    lines = []
    for key, qty in items:
        name, price = P[key]
        lines += [name, f"  Qty: {qty}    {money(price * qty)}", ""]
    total = sum(P[k][1] * q for k, q in items)
    arrive = date + timedelta(days=2)
    body = f"""Hello {CUSTOMER['name']},

Thank you for shopping with us. We'll send a confirmation when your items ship.

Order #{order_no}
Placed on {date:%B} {date.day}, {date.year}

Arriving: {arrive:%A, %B} {arrive.day}
Ship to: {CUSTOMER['name']}, {CUSTOMER['street']}, {CUSTOMER['city']}
Phone: {CUSTOMER['phone']}

Order Details
--------------------------------
{chr(10).join(lines)}--------------------------------
Item Subtotal: {money(total)}
Order Total: {money(total)}
Paid with Visa ending in 4417

RiverMart Online - this is a demo email for PlastiTrack.
"""
    return ("RiverMart Online <auto-confirm@rivermart.example>",
            f"Your RiverMart order #{order_no} has been placed", body)


def supervalu(date, items, rng):
    order_no = f"2000{rng.randint(100, 999)}-{rng.randint(10000000, 99999999)}"
    rows = [f"{P[k][0]} | Qty {q} | {money(P[k][1] * q)}" for k, q in items]
    total = sum(P[k][1] * q for k, q in items)
    body = f"""Thanks for your order, {CUSTOMER['first']}!

Order number: {order_no}
Order date: {date:%b %d, %Y}
Delivery address:
  {CUSTOMER['name']}
  {CUSTOMER['street']}
  {CUSTOMER['city']}

Items in this order ({len(items)})
{chr(10).join(rows)}

Subtotal: {money(total)}
Total: {money(total)}
Payment: Mastercard ****8820

Questions? Call us at 1-555-010-7788.
SuperValu Mart - demo email for PlastiTrack.
"""
    return ("SuperValu Mart <orders@supervalu.example>", f"SuperValu order {order_no} received", body)


def northstar(date, items, rng):
    order_no = f"{rng.randint(900000000, 999999999)}"
    blocks = []
    for key, qty in items:
        name, price = P[key]
        blocks.append(f"Item: {name}\nQuantity: {qty}\nPrice: {money(price * qty)}\n")
    total = sum(P[k][1] * q for k, q in items)
    body = f"""Hi {CUSTOMER['first']}, we got your order!

Order #{order_no}
Ordered: {date:%m/%d/%Y}
Email: {CUSTOMER['email']}

Shipping to
{CUSTOMER['name']}
{CUSTOMER['street']}
{CUSTOMER['city']}

What you ordered
{chr(10).join(blocks)}
Order total: {money(total)}

Northstar Goods - demo email for PlastiTrack.
"""
    return ("Northstar Goods <hello@northstar.example>", f"Northstar order #{order_no} confirmed", body)


STORES = {"rivermart": rivermart, "supervalu": supervalu, "northstar": northstar}


def main():
    rng = random.Random(7)
    os.makedirs(OUT_DIR, exist_ok=True)
    for i, (store, day, items) in enumerate(ORDERS, start=1):
        date = datetime.strptime(day, "%Y-%m-%d").replace(hour=rng.randint(8, 21), minute=rng.randint(0, 59))
        sender, subject, body = STORES[store](date, items, rng)
        eml = (f"From: {sender}\nTo: {CUSTOMER['name']} <{CUSTOMER['email']}>\nSubject: {subject}\n"
               f"Date: {date:%a, %d %b %Y %H:%M:00} -0500\nContent-Type: text/plain; charset=utf-8\n\n{body}")
        path = os.path.join(OUT_DIR, f"order_{i:02d}_{store}_{day}.eml")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(eml)
    print(f"wrote {len(ORDERS)} emails to {os.path.normpath(OUT_DIR)}")


if __name__ == "__main__":
    main()
