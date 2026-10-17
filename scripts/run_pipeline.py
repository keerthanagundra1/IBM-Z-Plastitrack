"""Command-line demo of the full pipeline on LinuxONE: emails -> line items -> predictions -> alerts.

    python scripts/run_pipeline.py                 # demo_emails/, template tips
    python scripts/run_pipeline.py --llm           # also generate tips with local Granite
"""
import argparse
import glob
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from plastitrack import llm  # noqa: E402
from plastitrack.insights import by, emails_to_items, repeat_alerts, summary  # noqa: E402
from plastitrack.predict import PlastiPredictor  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 55)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emails", default="demo_emails")
    ap.add_argument("--llm", action="store_true")
    args = ap.parse_args()

    raws = [open(p, encoding="utf-8").read() for p in sorted(glob.glob(os.path.join(args.emails, "*.eml")))]
    df, parsed = emails_to_items(raws, PlastiPredictor())
    pii = {}
    for r in parsed:
        for k, v in r["pii_removed"].items():
            pii[k] = pii.get(k, 0) + v
    print(f"Parsed {len(raws)} emails -> {len(df)} line items. Personal details removed: {pii}\n")
    print(df[["order_date", "store", "product", "quantity", "category", "plastic_level", "plastic_type",
              "confidence", "source", "plastic_g"]].to_string(index=False))

    s = summary(df)
    print(f"\nTotal: {s['total_g']:,.0f} g over {s['months']} months  (~{s['per_month_g']:,.0f} g/month); "
          f"{s['high_share']:.0%} of lines are medium/high plastic")
    print("\nBy month:\n", by(df, "month").to_string(index=False))
    print("\nBy category:\n", by(df, "category").to_string(index=False))
    print("\nBy store:\n", by(df, "store").to_string(index=False))

    alerts = repeat_alerts(df)
    print(f"\n{len(alerts)} repeat-purchase alerts:")
    for a in alerts:
        print(f"\n* {a['short']}  ({a['times']}x, {a['plastic_g']:.0f} g, {a['level']}/{a['type']})")
        print("  template:", a["tip"])
        if args.llm and llm.available():
            t0 = time.time()
            tip = llm.personalized_tip(a["product"], a["times"], round(a["plastic_g"]), a["swap"],
                                       round(a["saved_g"]))
            print(f"  granite ({time.time() - t0:.0f}s):", tip or "[rejected -> template used]")


if __name__ == "__main__":
    main()
