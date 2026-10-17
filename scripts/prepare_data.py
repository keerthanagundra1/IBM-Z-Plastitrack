"""Build the labeled training set from Open Food / Beauty / Products Facts dumps.

Streams each gzipped TSV in chunks (only the columns we need), labels packaging
with rule-based weak labels, and writes a sample to data/processed/products_labeled.csv.

Run on LinuxONE (inside the lab container), from the project root:
    python scripts/prepare_data.py --sample 200000
"""
import argparse
import csv
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from plastitrack.categories import category_group  # noqa: E402
from plastitrack.labels import label_packaging  # noqa: E402

SOURCES = {  # file in data/raw -> source name
    "off_products.csv.gz": "food",
    "obf_products.csv.gz": "beauty",
    "opf_products.csv.gz": "products",
}
COLUMNS = ["code", "product_name", "brands", "categories_en", "main_category_en", "quantity",
           "countries_en", "packaging", "packaging_tags", "packaging_text"]
ENGLISH_COUNTRIES = "United States|United Kingdom|Canada|Australia|Ireland|New Zealand"


def process_file(path, source, chunksize=200_000):
    """Yield labeled chunks (only rows with a product name and known packaging)."""
    reader = pd.read_csv(
        path, sep="\t", compression="gzip", dtype=str, chunksize=chunksize,
        usecols=lambda c: c in COLUMNS,     # tolerate files missing some columns
        quoting=csv.QUOTE_NONE, on_bad_lines="skip", low_memory=False,
    )
    for chunk in reader:
        chunk = chunk.reindex(columns=COLUMNS)
        chunk = chunk[chunk["product_name"].notna()]
        # need some packaging info to build a label
        has_pack = chunk["packaging_tags"].notna() | chunk["packaging_text"].notna() | chunk["packaging"].notna()
        chunk = chunk[has_pack].copy()
        if chunk.empty:
            continue
        pack_text = chunk["packaging_text"].fillna("") + " " + chunk["packaging"].fillna("")
        labels = [label_packaging(t, x) for t, x in zip(chunk["packaging_tags"], pack_text)]
        chunk["plastic_level"] = [lv for lv, _ in labels]
        chunk["plastic_type"] = [ty for _, ty in labels]
        chunk = chunk[chunk["plastic_level"].notna()]
        chunk["source"] = source
        yield chunk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--out", default="data/processed/products_labeled.csv")
    ap.add_argument("--sample", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    t0 = time.time()
    parts = []
    for fname, source in SOURCES.items():
        path = os.path.join(args.raw_dir, fname)
        if not os.path.exists(path):
            print(f"skip {fname} (not found)")
            continue
        n = 0
        for chunk in process_file(path, source):
            parts.append(chunk)
            n += len(chunk)
        print(f"{fname}: {n:,} labeled rows  ({time.time() - t0:.0f}s elapsed)")

    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates(subset=["code"]).drop_duplicates(subset=["product_name", "brands"])
    df["is_english"] = df["countries_en"].fillna("").str.contains(ENGLISH_COUNTRIES)
    print(f"total labeled (deduped): {len(df):,}  | english-market: {df['is_english'].sum():,}")

    # Sample: keep all English-market + all beauty/products rows (closest to our users'
    # US-style orders), then fill the rest randomly from other food rows.
    priority = df[df["is_english"] | (df["source"] != "food")]
    rest = df.drop(priority.index)
    if len(priority) >= args.sample:
        sample = priority.sample(args.sample, random_state=args.seed)
    else:
        fill = rest.sample(min(len(rest), args.sample - len(priority)), random_state=args.seed)
        sample = pd.concat([priority, fill])

    sample = sample.copy()
    sample["category_group"] = [
        category_group(c, m, p) for c, m, p in
        zip(sample["categories_en"], sample["main_category_en"], sample["product_name"])
    ]
    sample = sample.sample(frac=1, random_state=args.seed).reset_index(drop=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    sample.to_csv(args.out, index=False)

    print(f"\nwrote {len(sample):,} rows -> {args.out}  ({time.time() - t0:.0f}s total)")
    print("\nplastic_level:\n", sample["plastic_level"].value_counts().to_string())
    print("\nplastic_type:\n", sample["plastic_type"].value_counts().to_string())
    print("\nsource:\n", sample["source"].value_counts().to_string())
    print("\ncategory_group:\n", sample["category_group"].value_counts().to_string())


if __name__ == "__main__":
    main()
