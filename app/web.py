"""PlastiTrack web UI (Flask). Runs entirely on IBM LinuxONE.

    python app/web.py                       # http://127.0.0.1:8501
From your laptop, open an SSH tunnel and browse to http://localhost:8501 :
    ssh -i key.pem -L 8501:localhost:8501 linux1@<linuxone-ip>

Privacy design: raw emails are parsed and then discarded immediately. Only line items
(store, date, product, quantity, price) and the *redacted* preview are kept, in server
memory, for this browser session. Charts render with locally served Vega JS (no CDN calls).
"""
import glob
import os
import platform
import secrets
import sys
import time

import altair as alt
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from plastitrack import llm  # noqa: E402
from plastitrack.email_parser import split_pasted_emails  # noqa: E402
from plastitrack.insights import by, emails_to_items, repeat_alerts, summary, top_offenders  # noqa: E402
from plastitrack.predict import PlastiPredictor  # noqa: E402
from plastitrack.viz import LEVEL_COLORS, TYPE_COLORS  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("PLASTITRACK_SECRET", secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024      # 5 MB upload limit

PREDICTOR = PlastiPredictor(os.path.join(ROOT, "models"))
SESSIONS = {}           # session id -> {"items": DataFrame, "parsed": [...], "tips": {...}, "elapsed": s}
LEVELS = ["none", "low", "medium", "high"]
TYPE_LABELS = {"none": "none", "PET": "PET", "HDPE": "HDPE", "PP": "PP", "film": "film / LDPE",
               "mixed_other": "other / unspecified"}
BLUE = "#2a78d6"
AXIS = {"labelColor": "#8a8984", "titleColor": "#8a8984", "gridColor": "#8a898433", "domainColor": "#8a898466",
        "tickColor": "#8a898466", "labelFontSize": 12, "titleFontSize": 12}


def fmt_g(g):
    return f"{g / 1000:,.2f} kg" if g >= 1000 else f"{g:,.0f} g"


def tls_info():
    """Negotiated TLS version + cipher when served over HTTPS (gunicorn + OpenSSL), else None."""
    sock = request.environ.get("gunicorn.socket")
    if hasattr(sock, "cipher") and sock.cipher():
        name, version, _bits = sock.cipher()
        return f"{version} · {name}"
    return None


def state():
    sid = session.get("sid")
    return SESSIONS.get(sid) if sid else None


def _style(chart, height):
    return (chart.properties(height=height, width="container", background="transparent")
            .configure_axis(**AXIS).configure_legend(labelColor="#8a8984", titleColor="#8a8984", orient="bottom")
            .configure_view(stroke=None))


def build_charts(df):
    """Altair -> Vega-Lite JSON specs; the browser renders them with local vega-embed."""
    monthly = df.groupby(["month", "plastic_level"], as_index=False)["plastic_g"].sum()
    monthly["rank"] = monthly["plastic_level"].map(LEVELS.index)
    month_chart = alt.Chart(monthly).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("month:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("sum(plastic_g):Q", title="grams of plastic"),
        color=alt.Color("plastic_level:N", title="plastic level", sort=LEVELS,
                        scale=alt.Scale(domain=LEVELS, range=[LEVEL_COLORS[k] for k in LEVELS])),
        order=alt.Order("rank:Q"),
        tooltip=["month", alt.Tooltip("plastic_level", title="level"),
                 alt.Tooltip("plastic_g:Q", format=",.0f", title="grams")])

    def hbar(data, field, color=BLUE):
        return alt.Chart(data).mark_bar(color=color, cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
            y=alt.Y(f"{field}:N", sort="-x", title=None), x=alt.X("plastic_g:Q", title="grams of plastic"),
            tooltip=[field, alt.Tooltip("plastic_g:Q", format=",.0f", title="grams")])

    ptype = by(df[df["plastic_type"] != "none"], "plastic_type")
    ptype["label"] = ptype["plastic_type"].map(TYPE_LABELS)
    type_chart = alt.Chart(ptype).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
        y=alt.Y("label:N", sort="-x", title=None), x=alt.X("plastic_g:Q", title="grams of plastic"),
        color=alt.Color("plastic_type:N", legend=None,
                        scale=alt.Scale(domain=list(TYPE_COLORS), range=list(TYPE_COLORS.values()))),
        tooltip=[alt.Tooltip("label", title="type"), alt.Tooltip("plastic_g:Q", format=",.0f", title="grams")])

    return {"month": _style(month_chart, 260).to_json(),
            "category": _style(hbar(by(df, "category"), "category"), 260).to_json(),
            "store": _style(hbar(by(df, "store"), "store"), 140).to_json(),
            "ptype": _style(type_chart, 180).to_json()}


@app.route("/")
def index():
    st = state()
    ctx = {"machine": platform.machine(), "byteorder": sys.byteorder, "python": platform.python_version(),
           "llm_available": llm.available(), "llm_model": llm.model_name(), "type_labels": TYPE_LABELS, "fmt_g": fmt_g}
    ctx["tls"] = tls_info()
    if not st:
        return render_template("index.html", has_data=False, **ctx)
    df, parsed = st["items"], st["parsed"]
    alerts = repeat_alerts(df)
    for a in alerts:
        gen = st["tips"].get(a["product"])
        if gen:
            a["tip"], a["tip_source"] = gen, "granite"
    items = df.copy()
    items["order_date"] = items["order_date"].dt.date
    return render_template(
        "index.html", has_data=True, s=summary(df), charts=build_charts(df), alerts=alerts,
        saved_total=sum(a["saved_g"] for a in alerts), top=top_offenders(df).to_dict("records"),
        items=items.to_dict("records"), parsed=parsed, elapsed=st["elapsed"],
        pii_total=sum(sum(r["pii_removed"].values()) for r in parsed), **ctx)


@app.route("/demo")
def demo():
    """Shortcut: load the demo emails (handy for screenshots / the demo video)."""
    return analyze(source="demo")


@app.route("/analyze", methods=["POST"])
def analyze(source=None):
    source = source or request.form.get("source")
    if source in ("demo", "demo_plus"):
        pattern = ["*.eml"] + (["extra/*.eml"] if source == "demo_plus" else [])
        raws = [open(p, encoding="utf-8").read()
                for pat in pattern for p in sorted(glob.glob(os.path.join(ROOT, "demo_emails", pat)))]
    else:
        raws = [f.read().decode("utf-8", "replace") for f in request.files.getlist("files") if f.filename]
        pasted = request.form.get("pasted", "")
        if pasted.strip():
            raws += split_pasted_emails(pasted)
    t0 = time.time()
    df, parsed = emails_to_items(raws, PREDICTOR, llm_extract=llm.extract_items if llm.available() else None)
    elapsed = time.time() - t0
    del raws                                   # raw emails are not kept
    if df.empty:
        return render_template("index.html", has_data=False, error="No line items found in that input.",
                               machine=platform.machine(), byteorder=sys.byteorder,
                               python=platform.python_version(), llm_available=llm.available())
    for r in parsed:                           # keep only the redacted preview + counts
        r.pop("items", None)
    sid = session.get("sid") or secrets.token_hex(8)
    session["sid"] = sid
    SESSIONS[sid] = {"items": df, "parsed": parsed, "tips": {}, "elapsed": elapsed}
    return redirect(url_for("index", tab=request.args.get("tab")))   # /demo?tab=t2 opens a tab


@app.route("/personalize", methods=["POST"])
def personalize():
    """Generate tips with the local Granite LLM for the top-N alerts."""
    st = state()
    if not st or not llm.available():
        return jsonify({"ok": False, "error": "no data or LLM unavailable"}), 400
    n = int(request.form.get("n", 3))
    t0 = time.time()
    done = 0
    for a in repeat_alerts(st["items"])[:n]:
        if a["product"] not in st["tips"]:
            tip = llm.personalized_tip(a["product"], a["times"], round(a["plastic_g"]), a["swap"],
                                       round(a["saved_g"]))
            if tip:
                st["tips"][a["product"]] = tip
                done += 1
    return jsonify({"ok": True, "generated": done, "seconds": round(time.time() - t0, 1)})


@app.route("/download.csv")
def download():
    st = state()
    if not st:
        return redirect(url_for("index"))
    cols = ["order_date", "store", "product", "quantity", "price", "category", "plastic_level", "plastic_type",
            "confidence", "source", "why", "plastic_g"]
    return Response(st["items"][cols].to_csv(index=False), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=plastitrack_line_items.csv"})


@app.route("/clear", methods=["POST"])
def clear():
    SESSIONS.pop(session.pop("sid", None), None)
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok", "machine": platform.machine(), "byteorder": sys.byteorder, "llm": llm.available()}


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8501)), debug=False)
