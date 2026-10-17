"""End-to-end pipeline (emails -> scored line items) and the dashboard aggregates / alerts."""
import pandas as pd

from .email_parser import parse_email
from .swaps import short_name, suggest_swap, template_tip


def emails_to_items(raw_emails, predictor, llm_extract=None):
    """Parse + score a list of raw email texts. Returns (items DataFrame, list of parse results).

    Only line items are kept. The parse results are returned so the UI can show
    the redacted preview, then they are discarded (never written to disk).
    """
    rows, parsed = [], []
    for raw in raw_emails:
        r = parse_email(raw, llm_extract=llm_extract)
        parsed.append(r)
        rows.extend(r["items"])
    if not rows:
        return pd.DataFrame(), parsed
    df = pd.DataFrame(rows)
    preds = predictor.predict(df["product"].tolist(), df["quantity"].tolist())
    df = pd.concat([df, pd.DataFrame(preds)], axis=1)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    return df, parsed


def summary(df):
    """Headline numbers for the dashboard."""
    months = df["month"].nunique()
    return {"items": int(df["quantity"].sum()), "orders": int(df.groupby(["store", "order_date"]).ngroups),
            "total_g": float(df["plastic_g"].sum()), "months": months,
            "per_month_g": float(df["plastic_g"].sum() / max(months, 1)),
            "high_share": float((df["plastic_level"].isin(["medium", "high"])).mean())}


def by(df, col):
    return df.groupby(col, as_index=False)["plastic_g"].sum().sort_values("plastic_g", ascending=False)


def top_offenders(df, n=8):
    g = (df.groupby("product", as_index=False)
           .agg(plastic_g=("plastic_g", "sum"), times=("order_date", "nunique"),
                level=("plastic_level", "first"), category=("category", "first")))
    return g.sort_values("plastic_g", ascending=False).head(n)


def repeat_alerts(df, min_times=2, min_grams=20):
    """Products bought in >= min_times different orders with medium/high plastic -> alert + swap."""
    risky = df[df["plastic_level"].isin(["medium", "high"])]
    g = (risky.groupby("product", as_index=False)
              .agg(times=("order_date", "nunique"), plastic_g=("plastic_g", "sum"),
                   level=("plastic_level", "first"), ptype=("plastic_type", "first"),
                   category=("category", "first"), stores=("store", lambda s: ", ".join(sorted(set(s))))))
    g = g[(g["times"] >= min_times) & (g["plastic_g"] >= min_grams)].sort_values("plastic_g", ascending=False)
    alerts = []
    for _, r in g.iterrows():
        swap, reduction = suggest_swap(r["product"], r["category"])
        alerts.append({"product": r["product"], "short": short_name(r["product"]), "times": int(r["times"]),
                       "plastic_g": float(r["plastic_g"]), "level": r["level"], "type": r["ptype"],
                       "stores": r["stores"], "swap": swap, "saved_g": float(r["plastic_g"] * reduction),
                       "tip": template_tip(r["product"], int(r["times"]), r["plastic_g"], swap, reduction),
                       "tip_source": "template"})
    return alerts
