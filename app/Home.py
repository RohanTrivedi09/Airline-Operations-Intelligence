"""Airline Operations Intelligence Platform — dashboard entry point.

Run:  .venv/bin/streamlit run app/Home.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

st.set_page_config(page_title="Airline Operations Intelligence",
                   page_icon="✈️", layout="wide")

from utils import db, ui  # noqa: E402

ui.setup("Airline Operations Intelligence", "✈️",
         "US domestic flights, 2015 · 5,819,078 records · Big Data Analytics project")

source = db.source_name()
if source != "MongoDB":
    st.warning(f"Reading from **{source}** — start MongoDB with `docker compose up -d` "
               "for the full serving layer.")

k = db.kpis()
if not k:
    st.error("No data found. Run notebooks 01–08, then `docker compose up -d`.")
    st.stop()

ui.kpis([
    {"label": "Total flights", "value": f"{int(k['total_flights']):,}",
     "sub": f"{int(k.get('airlines',0))} airlines · {int(k.get('airports',0))} airports"},
    {"label": "On time", "value": f"{k['on_time_pct']:.1f}%",
     "sub": "arrived within 15 min", "tone": "good"},
    {"label": "Delayed", "value": f"{k['delay_rate']:.1f}%",
     "sub": "15+ min late", "tone": ui.tone_for_delay(k["delay_rate"])},
    {"label": "Avg arrival delay", "value": f"{k['avg_arr_delay']:.1f} min",
     "sub": f"departure {k['avg_dep_delay']:.1f} min"},
    {"label": "Cancelled", "value": f"{k['cancellation_rate']:.2f}%",
     "sub": f"diverted {k['diversion_rate']:.2f}%"},
])

ui.section("Where to go", "Each page answers one operational question.")

left, right = st.columns(2)
with left:
    st.markdown("""
| Page | Answers |
|---|---|
| **Overview** | How did the network perform, and how did it move through the year? |
| **Airlines** | Which carriers are reliable, adjusted for how much they fly? |
| **Airports** | Which airports struggle, when, and what type of airport are they? |
""")
with right:
    st.markdown("""
| Page | Answers |
|---|---|
| **Routes** | Which origin→destination pairs are reliable? |
| **Delay causes** | What causes delays, and when do they cluster? |
| **Prediction** | What is the delay risk for a flight that has not happened yet? |
""")

ui.section("How it works", "Every number here was precomputed by Apache Spark.")
st.markdown("""
```
Kaggle CSV   565 MB ─┐
NOAA weather 445 MB ─┴─▶ PySpark ETL ─▶ Parquet 201 MB
                              │
                              ├─▶ Spark aggregations + MLlib
                              └─▶ MongoDB 1.8 MB ─▶ dashboard
```
""")
ui.note(
    "<strong>The dashboard performs no aggregation.</strong> It reads a few hundred KB of "
    "precomputed documents instead of scanning 5.8 million rows, which is why every page "
    "responds instantly. All heavy computation happened once, in Spark."
)
ui.note(
    "<strong>Reading the rankings fairly.</strong> An airport with 76 flights can show a 44% "
    "delay rate on noise alone. Rankings therefore exclude very low-volume airports and "
    "routes, and sample sizes are shown throughout so you can judge each number yourself."
)
