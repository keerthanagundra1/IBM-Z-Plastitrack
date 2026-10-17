"""Local generative AI on LinuxONE: IBM Granite 4.0 via llama.cpp (llama-cpp-python).

Default model: granite-4.0-h-350m *instruct*, Q8_0, converted to big-endian for s390x
(see scripts/get_llm.sh). Fallback: the lab's granite-4.0-h-350m *base* model with a
few-shot completion prompt. No text ever leaves the machine.

Guardrails: every generated tip is checked (length, mentions the swap, and contains NO
numbers that were not in the input), otherwise callers use swaps.template_tip().
"""
import os
import re
import threading
from functools import lru_cache

_LOCK = threading.Lock()   # a llama.cpp model object is not thread-safe (gunicorn serves with threads)

_HERE = os.path.dirname(__file__)
INSTRUCT_PATH = os.environ.get(
    "PLASTITRACK_LLM",
    os.path.join(_HERE, "..", "..", "models", "llm", "granite-4.0-h-350m-Q8_0-be.gguf"))
BASE_PATH = "/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf"   # ships with the LinuxONE lab image

SYSTEM = ("You are PlastiTrack, a friendly sustainability coach. Write ONE tip of 2 sentences (under 45 words). "
          "Sentence 1: what the shopper keeps buying and how much plastic it added up to. "
          "Sentence 2: the swap and how much plastic it avoids. Use only the numbers given.")


def _facts(product, times, grams, swap, saved):
    return (f"Product: {product}\nBought: {times} times recently\nPlastic so far: about {grams:,} g\n"
            f"Swap: {swap}\nPlastic avoided: about {saved:,} g")


# one worked example teaches the format (one-shot)
EXAMPLE_USER = _facts("Dove Deep Moisture Body Wash, 22 fl oz", 3, 100, "bar soap in a paper wrapper", 90)
EXAMPLE_ANSWER = ("You have bought Dove body wash 3 times lately, which adds up to about 100 g of plastic. "
                  "Switching to a moisturizing bar soap in a paper wrapper keeps your routine and avoids about 90 g.")


def model_path():
    """Instruct model if present, else the lab's base model, else None."""
    for p in (INSTRUCT_PATH, BASE_PATH):
        if os.path.exists(p):
            return p
    return None


def model_name():
    p = model_path()
    return os.path.basename(p) if p else "none"


def available():
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return model_path() is not None


@lru_cache(maxsize=1)
def _load():
    from llama_cpp import Llama  # lazy import: the app still runs without llama_cpp
    return Llama(model_path=model_path(), n_ctx=2048, n_threads=os.cpu_count() or 2, verbose=False)


def chat(messages, max_tokens=120, temperature=0.2):
    """Chat completion with the instruct model (uses the GGUF's own chat template)."""
    with _LOCK:
        out = _load().create_chat_completion(messages=messages, max_tokens=max_tokens, temperature=temperature)
    return out["choices"][0]["message"]["content"].strip()


def _numbers(text):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def check_tip(text, facts, swap):
    """Guardrail: sane length, mentions the swap, and no invented numbers."""
    if not text or not (25 <= len(text) <= 360):
        return False
    if any(k in text for k in ("Product:", "Swap:", "Bought:")):
        return False
    swap_words = re.findall(r"[a-z]{4,}", swap.lower())[:4]
    if swap_words and not any(w in text.lower() for w in swap_words):
        return False
    return _numbers(text) <= _numbers(facts)          # every number must come from the input


@lru_cache(maxsize=256)
def personalized_tip(product, times, grams, swap, saved):
    """Return a generated tip, or None if generation fails the guardrails."""
    facts = _facts(product, times, grams, swap, saved)
    if model_path() == INSTRUCT_PATH:
        text = chat([{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": EXAMPLE_USER},
                     {"role": "assistant", "content": EXAMPLE_ANSWER},
                     {"role": "user", "content": facts}], max_tokens=90)
    else:   # base model: few-shot plain completion
        prompt = (f"{SYSTEM}\n\n{EXAMPLE_USER}\nTip: {EXAMPLE_ANSWER}\n\n{facts}\nTip:")
        with _LOCK:
            out = _load()(prompt, max_tokens=90, temperature=0.2, stop=["\n\n", "Product:"])
        text = out["choices"][0]["text"].strip()
    return text if check_tip(text, facts, swap) else None


# ---------------------------------------------------------------- email parsing fallback
EXTRACT_SYSTEM = ("Extract the purchased products from the order email. Reply with JSON only: "
                  '{"items": [{"product": string, "quantity": integer, "price": number}]}. '
                  "product = the product name as written (brand, name, size). price = total price paid for that "
                  "line in dollars. Do not include delivery, tax, totals or people.")


def _grounded(product, text):
    """Anti-hallucination: most words of the product name must appear in the email text."""
    words = [w for w in re.findall(r"[a-z0-9']{3,}", product.lower())]
    return bool(words) and sum(w in text.lower() for w in words) / len(words) >= 0.6


def extract_items(text):
    """Granite reads an (already redacted) email and returns line items as JSON.
    Only items whose name and price are found in the text are kept."""
    import json
    if model_path() != INSTRUCT_PATH:
        return []                                   # base model is not reliable for JSON
    with _LOCK:
        out = _load().create_chat_completion(
            messages=[{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": text[:3000]}],
            response_format={"type": "json_object"}, max_tokens=400, temperature=0)
    try:
        raw_items = json.loads(out["choices"][0]["message"]["content"]).get("items", [])
    except (ValueError, AttributeError):
        return []
    prices_in_text = {p.replace(",", "") for p in re.findall(r"\$\s?(\d[\d,]*\.\d{2})", text)}
    items = []
    for it in raw_items:
        try:
            product, qty, price = str(it["product"]).strip(), int(it.get("quantity", 1)), float(it["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if _grounded(product, text) and 1 <= qty <= 99 and f"{price:.2f}" in prices_in_text:
            items.append({"product": product, "quantity": qty, "price": price})
    return items
