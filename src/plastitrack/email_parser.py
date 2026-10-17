"""Parse order-confirmation emails into line items, and strip personal details.

Privacy rule: only {store, order_date, product, quantity, price} leave this module.
Names, emails, addresses, phone numbers, order numbers and card digits are never stored;
`redact()` exists so the UI can *show* the user what was removed.

Works on raw .eml text or on text pasted from an email client (no headers).
"""
import email
import re
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr

PRICE = r"\$\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)"

# --- layout-specific line-item patterns -------------------------------------------
# marketplace style:  "<product>\n  Qty: 2    $9.96"
RE_QTY_NEXT_LINE = re.compile(rf"^(?P<name>[^\n$|]{{4,}}?)\s*\n\s*Qty:?\s*(?P<qty>\d+)\s+{PRICE}", re.M | re.I)
# big-box style:      "<product> | Qty 1 | $3.48"
RE_PIPE = re.compile(rf"^(?P<name>[^\n|]{{4,}}?)\s*\|\s*Qty:?\s*(?P<qty>\d+)\s*\|\s*{PRICE}", re.M | re.I)
# department style:   "Item: <product>\nQuantity: 1\nPrice: $8.99"
RE_BLOCK = re.compile(rf"^Item:\s*(?P<name>[^\n]+)\n\s*Quantity:\s*(?P<qty>\d+)\s*\n\s*Price:\s*{PRICE}",
                      re.M | re.I)
# generic fallback:   "<product>  x2  $9.96"  or  "<product> ... $9.96"
RE_GENERIC = re.compile(rf"^(?P<name>[A-Za-z][^\n$]{{5,}}?)\s+(?:(?:x|qty:?)\s*(?P<qty>\d+)\s+)?{PRICE}\s*$",
                        re.M | re.I)

# lines that have a price but are not products (matched at the START of the line only,
# so "Colgate Total Toothpaste" is still a product)
NOT_PRODUCT = re.compile(r"^(?:item\s+|order\s+|estimated\s+)?(?:sub)?total|^(?:estimated\s+)?tax|^shipping|"
                         r"^delivery fee|^discount|^savings|^tip\b|^payment|^paid|^refund|^balance|^gift card", re.I)

KNOWN_STORES = {"rivermart": "RiverMart Online", "supervalu": "SuperValu Mart", "northstar": "Northstar Goods"}

# --- redaction patterns -------------------------------------------------------------
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_PHONE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}")
RE_ORDER_NO = re.compile(r"(order\s*(?:#|number|no\.?)?:?\s*)#?[\d-]{6,}", re.I)
RE_CARD = re.compile(r"((?:visa|mastercard|amex|discover|card)[^\n]{0,20}?(?:ending in|\*{2,}))\s*\d{4}", re.I)
RE_STREET = re.compile(r"\b\d{1,6}\s+(?:[A-Z][a-z]+\s){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|"
                       r"Drive|Dr|Court|Ct|Way|Place|Pl)\b\.?(?:\s*(?:Apt|Unit|Suite|#)\s*\w+)?")
RE_CITY_ZIP = re.compile(r"\b[A-Z][a-zA-Z .]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b")
# greeting words are case-insensitive, the captured name must be Capitalized
RE_GREETING = re.compile(r"^(?i:hello|hi|hey|dear|thanks for your order)[,!]?\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
                         re.M)


def _split_headers(raw):
    """Return (headers dict, body text). Pasted text without headers is all body."""
    if re.match(r"^(From|To|Subject|Date):", raw.lstrip(), re.I):
        msg = email.message_from_string(raw.lstrip())
        if msg.is_multipart():
            parts = [p.get_payload(decode=True) for p in msg.walk() if p.get_content_type() == "text/plain"]
            body = b"\n".join(p for p in parts if p).decode("utf-8", "replace")
        else:
            body = msg.get_payload()
        return {k.lower(): v for k, v in msg.items()}, body
    return {}, raw


def _detect_store(headers, body):
    sender = headers.get("from", "")
    display, addr = parseaddr(sender)
    blob = f"{sender} {body[-400:]}".lower()
    for key, name in KNOWN_STORES.items():
        if key in blob:
            return name
    if display:
        return display.strip()
    # pasted text without headers: "Your order from GreenGrocer" / "Thanks for shopping at X"
    m = re.search(r"(?:order from|shopping (?:at|with))\s+([A-Z][\w&'-]*(?:\s[A-Z][\w&'-]*){0,2})", body)
    if m:
        return m.group(1)
    domain = addr.split("@")[-1].split(".")[0] if "@" in addr else ""
    return domain.title() or "Unknown store"


def _detect_date(headers, body):
    if headers.get("date"):
        try:
            return parsedate_to_datetime(headers["date"]).date().isoformat()
        except (TypeError, ValueError):
            pass
    patterns = [(r"(\d{1,2}/\d{1,2}/\d{4})", "%m/%d/%Y"),
                (r"([A-Z][a-z]+ \d{1,2}, \d{4})", "%B %d, %Y"),
                (r"([A-Z][a-z]{2} \d{1,2}, \d{4})", "%b %d, %Y"),
                (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d")]
    for pat, fmt in patterns:
        for m in re.finditer(pat, body):
            try:
                return datetime.strptime(m.group(1), fmt).date().isoformat()
            except ValueError:
                continue
    return datetime.today().date().isoformat()


def _to_float(s):
    return float(s.replace(",", ""))


def extract_items(body):
    """Try each layout; return the first that finds items. Each item: product, quantity, price."""
    for pattern in (RE_BLOCK, RE_PIPE, RE_QTY_NEXT_LINE, RE_GENERIC):
        items = []
        for m in pattern.finditer(body):
            name = re.sub(r"\s+", " ", m.group("name")).strip(" -:*•\t")
            if NOT_PRODUCT.search(name) or len(name) < 4:
                continue
            qty = int(m.group("qty")) if m.groupdict().get("qty") else 1
            items.append({"product": name, "quantity": qty, "price": _to_float(m.group(m.lastindex))})
        if items:
            return items, pattern is not RE_GENERIC
    return [], False


def redact(text, extra_names=()):
    """Replace personal details with tags. Returns (redacted_text, counts per kind)."""
    counts = {}

    def sub(pattern, repl, s, kind):
        new, n = pattern.subn(repl, s)
        if n:
            counts[kind] = counts.get(kind, 0) + n
        return new

    names = set(n for n in extra_names if n)
    names |= {m.group(1) for m in RE_GREETING.finditer(text)}
    for full in list(names):            # also catch first / last names on their own
        names |= set(full.split())
    names = {n for n in names if len(n) > 2 and n.lower() not in {"for", "your", "order", "you"}}

    text = sub(RE_EMAIL, "[EMAIL]", text, "email")
    text = sub(RE_CARD, r"\1 [CARD]", text, "card")
    text = sub(RE_ORDER_NO, r"\1[ORDER-ID]", text, "order number")
    text = sub(RE_PHONE, "[PHONE]", text, "phone")
    text = sub(RE_STREET, "[ADDRESS]", text, "address")
    text = sub(RE_CITY_ZIP, "[CITY-ZIP]", text, "address")
    for n in sorted(names, key=len, reverse=True):
        text = sub(re.compile(rf"\b{re.escape(n)}\b"), "[NAME]", text, "name")
    return text, counts


def parse_email(raw, llm_extract=None):
    """Full pipeline for one email -> dict with store, date, items, redacted preview, pii counts.

    llm_extract: optional callable(redacted_text) -> items. Used only when the rule-based
    layouts find nothing, and it only ever sees the REDACTED text.
    """
    headers, body = _split_headers(raw)
    to_name = parseaddr(headers.get("to", ""))[0]
    store = _detect_store(headers, body)
    order_date = _detect_date(headers, body)
    items, structured = extract_items(body)
    # what the user sees in the privacy panel (headers included, then redacted)
    header_txt = "".join(f"{k.title()}: {headers[k]}\n" for k in ("from", "to", "subject", "date") if k in headers)
    redacted, pii = redact(header_txt + "\n" + body, extra_names=[to_name])
    parsed_by = "rules" if items else "none"
    if not items and llm_extract is not None:
        items = llm_extract(redact(body, extra_names=[to_name])[0])
        parsed_by = "granite" if items else "none"
    for it in items:
        it.update(store=store, order_date=order_date, parsed_by=parsed_by)
    return {"store": store, "order_date": order_date, "items": items, "structured": structured,
            "parsed_by": parsed_by,
            "redacted_text": redacted, "pii_removed": pii}


def split_pasted_emails(text):
    """Pasted blob with several emails -> list of emails (split on 'From:' header lines)."""
    parts = re.split(r"\n(?=From:\s)", text.strip())
    return [p for p in parts if p.strip()]


if __name__ == "__main__":
    import glob
    import os
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "demo_emails")
    total = 0
    for path in sorted(glob.glob(os.path.join(folder, "*.eml"))):
        with open(path, encoding="utf-8") as f:
            r = parse_email(f.read())
        total += len(r["items"])
        print(f"{os.path.basename(path):40} {r['store']:18} {r['order_date']}  items={len(r['items'])}  "
              f"pii={r['pii_removed']}")
    print("total line items:", total)
