"""Delay risk for a hypothetical flight.

Scored by the exported serving model (`scripts/export_serving_model.py`), not by the
Spark GBT it reproduces. Streamlit Community Cloud has no JVM, so a
`GBTClassificationModel` cannot be loaded there; training stays distributed, serving does
not need to be. The two agree to 0.0015 ROC-AUC on equivalent splits, and the page shows
both numbers rather than quietly substituting one for the other. See D6 in
`docs/engineering_decisions.md`.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Prediction", page_icon=":material/model_training:", layout="wide")
ui.setup('Delay Risk Prediction', 'Model performance and what-if scoring')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS = PROJECT_ROOT / "data" / "models"
RESULTS_JSON = PROJECT_ROOT / "data" / "marts" / "ml_classification_results.json"

SERVING_DIR = MODELS / "serving"

payload = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else {}


@st.cache_resource
def load_serving_model():
    """Load the exported model and its metadata, or (None, None) if not yet built."""
    meta_path = SERVING_DIR / "serving_model.json"
    model_path = SERVING_DIR / "hgb_delay_classifier.joblib"
    if not (meta_path.exists() and model_path.exists()):
        return None, None
    import joblib
    return joblib.load(model_path), json.loads(meta_path.read_text())


MODEL, META = load_serving_model()
THRESHOLD = (META or {}).get("threshold", payload.get("best_threshold", 0.5))

# ---------------------------------------------------------------- model performance
ablation = payload.get("ablation", [])
if ablation:
    st.subheader("How the model was built")
    st.caption("Each change measured on the same held-out test split of "
               f"{payload.get('test_rows', 0):,} flights. A step that did not help is kept "
               "in the table as a null result rather than dropped.")
    tbl = pd.DataFrame(ablation)[["step", "roc_auc", "f1", "recall", "precision", "threshold"]]
    ui.table(tbl, overrides={
        "step": st.column_config.Column("Step", width="large"),
        **{c: st.column_config.NumberColumn(c.replace("_", " ").upper(), format="%.4f")
           for c in ("roc_auc", "f1", "recall", "precision")},
        "threshold": st.column_config.NumberColumn("Threshold", format="%.2f"),
    })

    temporal = payload.get("temporal_check")
    if temporal:
        best = max(ablation, key=lambda r: r["f1"])
        c1, c2 = st.columns(2)
        # The delta must be a real signed number. Passing a label like "F1 0.3389"
        # gives Streamlit nothing to parse, so it renders an UP arrow next to the
        # worse result. Default colouring is also correct here: for ROC-AUC, down
        # is bad, which is exactly what `normal` means.
        c1.metric("ROC-AUC — random split", f"{best['roc_auc']:.4f}",
                  f"F1 {best['f1']:.4f}", delta_color="off")
        c2.metric("ROC-AUC — temporal split (Jan–Sep → Oct–Dec)",
                  f"{temporal['roc_auc']:.4f}",
                  f"{temporal['roc_auc'] - best['roc_auc']:+.4f} vs random split")
        st.warning(
            "**The temporal number is the honest one for forecasting.** A random split lets "
            "the model learn from days adjacent to the ones it predicts. Splitting on time "
            "instead drops ROC-AUC from "
            f"{best['roc_auc']:.3f} to {temporal['roc_auc']:.3f} — partly because the delay "
            "rate itself shifts from 19.45% (Jan–Sep) to 16.07% (Oct–Dec)."
        )

if META:
    ui.note(
        "<strong>Which model scores the flight below.</strong> The table above is the "
        "Spark MLlib ablation — that is where the modelling work happened. Scoring here "
        "uses an exported scikit-learn model with the identical feature set, because this "
        f"dashboard runs without a JVM. It reaches <strong>ROC-AUC {META['roc_auc']:.4f}</strong> "
        f"against the Spark GBT's <strong>0.7134</strong> (F1 {META['f1']:.4f} vs 0.4165), "
        "on its own equivalent split. The two are the same model in every way that "
        "matters; showing both numbers is how you can check that claim rather than take it."
    )

st.divider()
st.subheader("Estimate risk for a flight")

airlines = db.load("airline_metrics")
airports = db.load("airport_metrics")
routes = db.load("route_metrics")
if airlines.empty or airports.empty:
    st.error("Reference data missing. Run notebooks 05–08.")
    st.stop()

c1, c2, c3 = st.columns(3)
airline_name = c1.selectbox("Airline", sorted(airlines["airline_name"]))
airline_code = airlines.loc[airlines.airline_name == airline_name, "airline_code"].iloc[0]
codes = sorted(airports["airport_code"])
origin = c2.selectbox("Origin", codes, index=codes.index("LAX") if "LAX" in codes else 0)
dest = c3.selectbox("Destination", codes, index=codes.index("JFK") if "JFK" in codes else 1)

c4, c5, c6 = st.columns(3)
month = c4.slider("Month", 1, 12, 7)
dow = c5.selectbox("Day of week", [1, 2, 3, 4, 5, 6, 7],
                   format_func=lambda d: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d - 1])
hour = c6.slider("Scheduled departure hour", 0, 23, 17)

st.markdown("**Weather at origin** — the model uses these directly (notebook 11).")
w1, w2, w3 = st.columns([2, 1, 1])
condition = w1.selectbox(
    "Conditions",
    ["Typical for this airport and month", "Clear", "Rain", "Fog / low visibility",
     "Snow", "Thunderstorm", "Freezing precipitation"])
wind = w2.slider("Wind speed (m/s)", 0, 25, 4)
temp = w3.slider("Temperature (°C)", -30, 45, 20)

if origin == dest:
    st.error("Origin and destination must differ.")
    st.stop()

route_row = routes[(routes.origin == origin) & (routes.destination == dest)]
distance = int(route_row.iloc[0]["distance"]) if not route_row.empty else 1000
st.caption(f"Route distance: {distance:,} miles"
           + ("" if not route_row.empty else " — estimated; route not flown in 2015"))


def lookup(collection: str, keys: dict, column: str, default: float) -> float:
    """Read one smoothed rate from its lookup mart, falling back to the global rate."""
    df = db.load(collection)
    if df.empty or column not in df.columns:
        return default
    mask = pd.Series(True, index=df.index)
    for k, v in keys.items():
        if k not in df.columns:
            return default
        mask &= (df[k] == v)
    hit = df[mask]
    return float(hit.iloc[0][column]) if not hit.empty else default


if MODEL is None:
    st.error("Serving model not found. Build it with "
             "`.venv/bin/python scripts/export_serving_model.py`.")
    st.stop()

if st.button("Predict delay risk", type="primary"):
    with st.spinner("Scoring…"):
        defaults = db.load("inference_defaults")
        g = float(defaults.iloc[0]["global_delay_rate"]) if not defaults.empty else 0.1861

        # Weather: start from this airport's climatology for the month, then apply
        # whatever condition the user selected.
        clim = db.load("weather_climatology")
        row_w = clim[(clim.origin == origin) & (clim.month == month)] if not clim.empty else pd.DataFrame()
        wx = row_w.iloc[0].to_dict() if not row_w.empty else {}

        flags = {k: 0 for k in ["wx_thunderstorm", "wx_snow", "wx_rain",
                                "wx_fog", "wx_freezing", "wx_haze_smoke"]}
        vis, ceiling, precip = 16000.0, 22000.0, 0.0
        if condition == "Typical for this airport and month":
            flags = {k: float(wx.get(k, 0) or 0) for k in flags}
            vis = float(wx.get("visibility_m") or 16000)
            ceiling = float(wx.get("ceiling_m") or 22000)
            precip = float(wx.get("precip_mm") or 0)
        elif condition == "Rain":
            flags["wx_rain"] = 1; vis, ceiling, precip = 8000.0, 3000.0, 2.5
        elif condition == "Fog / low visibility":
            flags["wx_fog"] = 1; vis, ceiling = 1200.0, 300.0
        elif condition == "Snow":
            flags["wx_snow"] = 1; vis, ceiling, precip = 2000.0, 800.0, 5.0
        elif condition == "Thunderstorm":
            flags["wx_thunderstorm"] = 1; flags["wx_rain"] = 1
            vis, ceiling, precip = 4000.0, 1500.0, 8.0
        elif condition == "Freezing precipitation":
            flags["wx_freezing"] = 1; vis, ceiling, precip = 2500.0, 600.0, 3.0

        record = {
            "airline_code": airline_code,
            "time_of_day": ("night" if hour < 6 else "morning" if hour < 12
                            else "afternoon" if hour < 18 else "evening"),
            "season": ("winter" if month in (12, 1, 2) else "spring" if month in (3, 4, 5)
                       else "summer" if month in (6, 7, 8) else "autumn"),
            "month": month, "day_of_week": dow, "sched_dep_hour": hour,
            "distance": distance, "sched_duration": max(int(distance / 7) + 30, 40),
            "is_weekend_int": 1 if dow in (6, 7) else 0,
            "origin_delay_rate":  lookup("rate_origin", {"origin": origin}, "origin_delay_rate", g),
            "dest_delay_rate":    lookup("rate_destination", {"destination": dest}, "dest_delay_rate", g),
            "airline_delay_rate": lookup("rate_airline", {"airline_code": airline_code}, "airline_delay_rate", g),
            "route_delay_rate":   lookup("rate_route", {"route": f"{origin}-{dest}"}, "route_delay_rate", g),
            "origin_hour_delay_rate": lookup("rate_origin_hour",
                                             {"origin": origin, "sched_dep_hour": hour},
                                             "origin_hour_delay_rate", g),
            "airline_origin_delay_rate": lookup("rate_airline_origin",
                                                {"airline_code": airline_code, "origin": origin},
                                                "airline_origin_delay_rate", g),
            "temp_c": float(temp),
            "dewpoint_c": float(wx.get("dewpoint_c") or temp - 5),
            "wind_speed": float(wind),
            "visibility_m": vis, "ceiling_m": ceiling, "precip_mm": precip,
            **flags,
        }

        # Build the design matrix exactly as export_serving_model.py did: numeric
        # columns first in their recorded order, then the categoricals with their
        # training levels. Column order and category levels are part of the model.
        frame = pd.DataFrame([record])
        X = frame[META["numeric_features"]].astype("float32")
        for c in META["categorical_features"]:
            X[c] = pd.Categorical(frame[c], categories=META["category_levels"][c])
        prob = float(MODEL.predict_proba(X)[0, 1])

    # Risk band as a native badge rather than a coloured circle: the colour is
    # carried by the badge, and the word is carried by the label, so the meaning
    # survives for anyone who cannot distinguish the colours.
    if prob >= THRESHOLD + 0.15:
        band, tone, mark = "High risk", "red", ":material/trending_up:"
    elif prob >= THRESHOLD:
        band, tone, mark = "Elevated risk", "orange", ":material/warning:"
    else:
        band, tone, mark = "Low risk", "green", ":material/check_circle:"

    st.divider()
    with st.container(border=True):
        a, b = st.columns([1, 2])
        with a:
            # `inverse` because a HIGHER delay probability is worse. This is the
            # opposite of the ROC-AUC metrics above, where higher is better -- the
            # colour has to follow the meaning of the quantity, not the sign.
            st.metric("Delay probability", f"{prob*100:.1f}%",
                      f"{(prob - g) * 100:+.1f} pp vs network", delta_color="inverse")
            st.badge(band, color=tone, icon=mark)
        with b:
            st.progress(min(prob, 1.0))
            st.caption(
                f"Estimated **{prob*100:.1f}%** chance of arriving 15+ minutes late, against "
                f"a network average of {g*100:.1f}%. The decision threshold is "
                f"**{THRESHOLD}**, chosen by sweeping for best F1 — flights above it are "
                "predicted delayed."
            )
    st.info(
        "**What the model cannot see.** It uses only pre-departure information. It does not "
        "know whether the inbound aircraft is already running late — the single largest cause "
        "of delay minutes (39.8%) — nor same-day air-traffic-control decisions. Notebook 12 "
        "puts a number on that blindness: given the inbound's actual delay, ROC-AUC rises "
        "from 0.71 to 0.83. Treat this as a historical risk profile, not a forecast."
    )

# ---------------------------------------------------------------- importance
st.divider()
st.subheader("What drives the prediction")
fi = payload.get("feature_importances", {})
if fi:
    fdf = pd.DataFrame({"feature": list(fi)[:14], "importance": list(fi.values())[:14]})
    st.plotly_chart(charts.bar(fdf.sort_values("importance"), "importance", "feature",
                               "Gradient-Boosted Trees — feature importance", orientation="h"),
                    width="stretch")
    share = payload.get("weather_importance_share")
    if share:
        st.caption(
            f"Weather accounts for **{share*100:.1f}%** of total importance. The strongest "
            "single feature is `origin_hour_delay_rate` — the airport-by-hour interaction — "
            "confirming that congestion is hour-specific rather than a property of the airport."
        )
