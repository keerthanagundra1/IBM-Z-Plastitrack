"""Local generative AI on LinuxONE: IBM Granite 4.0 (350M, big-endian GGUF) via llama.cpp.

Used to personalize swap tips. No text ever leaves the machine: the model file is local
and llama.cpp runs on the s390x CPU. If the model is missing or the output looks wrong,
callers fall back to `swaps.template_tip()`.
"""
import os
import re
from functools import lru_cache

MODEL_PATH = os.environ.get("PLASTITRACK_LLM", "/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf")

# Few-shot examples teach the base model the format (it is not an instruction-tuned model).
FEW_SHOT = """Write a short, friendly tip that helps a shopper cut plastic packaging. Use only the numbers given.

Product: Pure Life Purified Water, 16.9 Fl Oz (Pack of 24)
Bought: 6 times, about 1,400 g of plastic
Swap: a filter pitcher plus a reusable bottle (avoids about 1,330 g)
Tip: You've bought bottled water 6 times lately, about 1,400 g of PET plastic. A filter pitcher and a reusable bottle would avoid about 1,330 g and save money too.

Product: Dove Deep Moisture Body Wash, 22 fl oz
Bought: 3 times, about 90 g of plastic
Swap: bar soap in a paper wrapper (avoids about 81 g)
Tip: Your body wash adds up to about 90 g of plastic bottles. A moisturizing bar soap in paper keeps the routine and avoids about 81 g.

"""


@lru_cache(maxsize=1)
def _load():
    from llama_cpp import Llama  # imported lazily: the app still runs if llama_cpp is missing
    return Llama(model_path=MODEL_PATH, n_ctx=1024, n_threads=os.cpu_count() or 2, verbose=False)


def available():
    try:
        import llama_cpp  # noqa: F401
        return os.path.exists(MODEL_PATH)
    except ImportError:
        return False


@lru_cache(maxsize=256)
def personalized_tip(product, times, grams, swap, saved):
    """Return a generated tip, or None if the output fails basic checks."""
    prompt = (FEW_SHOT + f"Product: {product}\nBought: {times} times, about {grams:,.0f} g of plastic\n"
              f"Swap: {swap} (avoids about {saved:,.0f} g)\nTip:")
    out = _load()(prompt, max_tokens=70, temperature=0.3, top_p=0.9, stop=["\n\n", "Product:"])
    text = out["choices"][0]["text"].strip()
    # sanity checks: right length, mentions the swap idea, no stray prompt fragments
    swap_words = [w for w in re.findall(r"[a-z]{4,}", swap.lower())][:3]
    if not (25 <= len(text) <= 320) or "Swap:" in text or "Bought:" in text:
        return None
    if swap_words and not any(w in text.lower() for w in swap_words):
        return None
    return text
