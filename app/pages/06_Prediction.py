"""Delay risk for a hypothetical flight, using the Random Forest from notebook 06.

Spark is started lazily and only on this page: loading a SparkSession costs ~20s, and
the other five pages need nothing but MongoDB reads.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db

st.set_page_config(page_title="Prediction", page_icon="🔮", layout="wide")
st.title("🔮 Delay Risk Prediction")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS = PROJECT_ROOT / "data" / "models"

results = db.load("ml_classification_results")
if not results.empty:
    st.subheader("Model performance")
    st.caption("Measured on a held-out 20% test split of 1,143,441 flights.")
    show = results[["model_name", "accuracy", "precision", "recall", "f1",
                    "roc_auc", "baseline_accuracy"]]
    st.dataframe(show, hide_index=True, width="stretch")
    st.warning(
        "**Read accuracy carefully.** A model that always predicts 'on time' scores "
        "**81.4%** because only 18.6% of flights are delayed. These models deliberately "
        "score *lower* accuracy in exchange for actually catching delays — recall is ~63%. "
        "ROC-AUC (~0.66) is the fair summary, and it is well above the 0.50 of guessing."
    )

st.markdown("---")
st.subheader("Estimate risk for a flight")

airlines = db.load("airline_metrics")
airports = db.load("airport_metrics")
routes = db.load("route_metrics")

if airlines.empty or airports.empty:
    st.error("Reference data missing. Run notebooks 05-08.")
    st.stop()

c1, c2, c3 = st.columns(3)
airline_name = c1.selectbox("Airline", sorted(airlines["airline_name"]))
airline_code = airlines[airlines["airline_name"] == airline_name].iloc[0]["airline_code"]
codes = sorted(airports["airport_code"])
origin = c2.selectbox("Origin", codes, index=codes.index("LAX") if "LAX" in codes else 0)
dest = c3.selectbox("Destination", codes, index=codes.index("JFK") if "JFK" in codes else 1)

c4, c5, c6 = st.columns(3)
month = c4.slider("Month", 1, 12, 7)
dow = c5.selectbox("Day of week", [1, 2, 3, 4, 5, 6, 7],
                   format_func=lambda d: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d - 1])
hour = c6.slider("Scheduled departure hour", 0, 23, 17)

if origin == dest:
    st.error("Origin and destination must differ.")
    st.stop()

route_row = routes[(routes["origin"] == origin) & (routes["destination"] == dest)]
distance = int(route_row.iloc[0]["distance"]) if not route_row.empty else 1000
st.caption(f"Route distance: {distance:,} miles"
           + ("" if not route_row.empty else " (estimated — route not flown in 2015)"))

if st.button("Predict delay risk", type="primary"):
    with st.spinner("Starting Spark and loading the model (~20s on first run)…"):
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from config import build_spark
        from pyspark.ml import PipelineModel
        from pyspark.ml.classification import RandomForestClassificationModel

        spark = build_spark("dashboard-prediction")
        prep = PipelineModel.load(str(MODELS / "feature_pipeline"))
        model = RandomForestClassificationModel.load(str(MODELS / "rf_delay_classifier"))

        GLOBAL_RATE = 0.1861

        def rate(df, key_col, key, col):
            if df.empty or key_col not in df:
                return GLOBAL_RATE
            hit = df[df[key_col] == key]
            return float(hit.iloc[0][col]) / 100.0 if not hit.empty else GLOBAL_RATE

        time_of_day = ("night" if hour < 6 else "morning" if hour < 12
                       else "afternoon" if hour < 18 else "evening")
        season = ("winter" if month in (12, 1, 2) else "spring" if month in (3, 4, 5)
                  else "summer" if month in (6, 7, 8) else "autumn")

        row = pd.DataFrame([{
            "airline_code": airline_code, "time_of_day": time_of_day, "season": season,
            "month": month, "day_of_week": dow, "sched_dep_hour": hour,
            "distance": distance, "sched_duration": max(int(distance / 7) + 30, 40),
            "is_weekend_int": 1 if dow in (6, 7) else 0,
            "origin_delay_rate": rate(airports, "airport_code", origin, "delay_rate"),
            "dest_delay_rate": rate(airports, "airport_code", dest, "delay_rate"),
            "airline_delay_rate": rate(airlines, "airline_code", airline_code, "delay_rate"),
            "route_delay_rate": (float(route_row.iloc[0]["delay_rate"]) / 100.0
                                 if not route_row.empty else GLOBAL_RATE),
            "weight": 1.0,
        }])

        sdf = spark.createDataFrame(row)
        pred = model.transform(prep.transform(sdf)).select("probability", "prediction").first()
        prob = float(pred["probability"][1])
        spark.stop()

    band, colour = (("HIGH", "🔴") if prob >= 0.60 else
                    ("MEDIUM", "🟠") if prob >= 0.40 else ("LOW", "🟢"))
    st.markdown("---")
    a, b = st.columns([1, 2])
    a.metric("Delay probability", f"{prob*100:.1f}%")
    a.markdown(f"### {colour} {band} RISK")
    with b:
        st.progress(min(prob, 1.0))
        st.caption(
            f"The model estimates a **{prob*100:.1f}%** chance this flight arrives 15+ minutes "
            f"late, against a network average of 18.6%. Bands: low <40%, medium 40–60%, high ≥60% "
            "— thresholds chosen for interpretation, not tuned."
        )
    st.info(
        "**What this can and cannot know.** It uses only information available before "
        "departure: airline, airports, schedule, distance, and historical rates. It cannot "
        "see the weather that day, whether the inbound aircraft is already late (the single "
        "largest cause of delay minutes), or air-traffic-control decisions. Treat it as a "
        "historical risk profile, not a forecast."
    )

imp = db.load("ml_classification_results")
st.markdown("---")
st.subheader("What drives the prediction")
import json
imp_path = PROJECT_ROOT / "data" / "marts" / "ml_classification_results.json"
if imp_path.exists():
    payload = json.loads(imp_path.read_text())
    fi = payload.get("feature_importances", {})
    if fi:
        fdf = pd.DataFrame({"feature": list(fi)[:12], "importance": list(fi.values())[:12]})
        st.plotly_chart(charts.bar(fdf.sort_values("importance"), "importance", "feature",
                                   "Random Forest feature importance", orientation="h"),
                        width="stretch")
        st.caption("Scheduled departure hour dominates: delay risk compounds through the day.")
