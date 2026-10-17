"""Inference throughput / latency benchmark on LinuxONE.

    python scripts/benchmark.py            # writes reports/benchmark.json
Measures: email parsing, batch scoring (items/s), single-item latency (p50/p95), Granite tip latency.
"""
import glob
import json
import os
import platform
import statistics
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from plastitrack import llm  # noqa: E402
from plastitrack.email_parser import parse_email  # noqa: E402
from plastitrack.predict import PlastiPredictor  # noqa: E402


def timeit(fn, repeat=3):
    best = float("inf")
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


def main():
    res = {"machine": platform.machine(), "byteorder": sys.byteorder, "cpus": os.cpu_count()}
    print(f"=== PlastiTrack benchmark on {res['machine']} ({res['byteorder']}-endian), {res['cpus']} vCPUs ===")

    # 1) email parsing + redaction
    raws = [open(p, encoding="utf-8").read() for p in sorted(glob.glob("demo_emails/*.eml"))] * 50
    secs = timeit(lambda: [parse_email(r) for r in raws])
    res["emails_per_s"] = round(len(raws) / secs)
    print(f"Email parse + PII redaction : {res['emails_per_s']:>8,} emails/s   ({len(raws)} emails)")

    # 2) batch scoring on real product titles
    df = pd.read_csv("data/processed/products_labeled.csv", dtype=str, keep_default_na=False, nrows=50000)
    titles = [f"{b} {n} {q}".strip() for n, b, q in zip(df["product_name"], df["brands"], df["quantity"])]
    pred = PlastiPredictor()
    pred.predict(titles[:100])                                     # warm-up
    for n in (1000, 10000, 50000):
        secs = timeit(lambda: pred.predict(titles[:n]), repeat=1)
        res[f"items_per_s_batch_{n}"] = round(n / secs)
        print(f"Batch scoring {n:>6,} items   : {n / secs:>8,.0f} items/s   ({secs:.2f} s)")

    # 2b) same batch split across all LinuxONE cores (one chunk per process)
    from joblib import Parallel, delayed
    n, k = 50000, os.cpu_count()
    chunks = [titles[i::k] for i in range(k)]
    Parallel(n_jobs=k)(delayed(pred.predict)(c[:50]) for c in chunks)           # start workers
    t0 = time.perf_counter()
    Parallel(n_jobs=k)(delayed(pred.predict)(c) for c in chunks)
    secs = time.perf_counter() - t0
    res["items_per_s_parallel"] = round(n / secs)
    print(f"Parallel {k} cores, {n:,} items: {n / secs:>8,.0f} items/s   ({secs:.2f} s)")

    # 3) single-item latency (what one web request feels like)
    lat = []
    for t in titles[:300]:
        t0 = time.perf_counter()
        pred.predict([t])
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    res["single_item_ms_p50"] = round(statistics.median(lat), 2)
    res["single_item_ms_p95"] = round(lat[int(0.95 * len(lat))], 2)
    print(f"Single-item latency         : p50 {res['single_item_ms_p50']} ms, p95 {res['single_item_ms_p95']} ms")

    # 4) Granite tip generation
    if llm.available():
        llm.personalized_tip.cache_clear()
        times = []
        for i in range(3):
            t0 = time.perf_counter()
            llm.personalized_tip(f"Brand {i} Sparkling Water, 12 fl oz (Pack of 12)", 3 + i, 300 + i, "a home carbonation maker", 180 + i)
            times.append(time.perf_counter() - t0)
        res["llm_model"] = llm.model_name()
        res["llm_tip_seconds_avg"] = round(sum(times[1:]) / 2, 1)   # skip first call (model load)
        print(f"Granite tip ({res['llm_model']}) : {res['llm_tip_seconds_avg']} s per tip")

    os.makedirs("reports", exist_ok=True)
    with open("reports/benchmark.json", "w") as f:
        json.dump(res, f, indent=2)
    print("saved reports/benchmark.json")


if __name__ == "__main__":
    main()
