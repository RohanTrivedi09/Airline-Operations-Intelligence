import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
ui.setup('Executive Overview', '📊', 'Network performance across 2015')

k = db.kpis()
if not k:
    st.error("No data. Run the notebooks first.")
    st.stop()

ui.kpis([
    {"label": "Total flights", "value": f"{int(k['total_flights']):,}"},
    {"label": "On time", "value": f"{k['on_time_pct']:.1f}%",
     "sub": "arrived within 15 min", "tone": "good"},
    {"label": "Delayed", "value": f"{k['delay_rate']:.1f}%", "sub": "15+ min late",
     "tone": ui.tone_for_delay(k["delay_rate"])},
    {"label": "Avg dep delay", "value": f"{k['avg_dep_delay']:.1f} min"},
    {"label": "Cancelled", "value": f"{k['cancellation_rate']:.2f}%"},
])

st.markdown("---")
monthly = db.trends("monthly")
if not monthly.empty:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(charts.line(monthly, "period", "delay_rate",
                                    "Delay rate by month (%)"), width="stretch")
    with right:
        st.plotly_chart(charts.line(monthly, "period", "avg_delay",
                                    "Average arrival delay by month (min)"),
                        width="stretch")

st.markdown("---")
ui.section("Airlines", "Ranked by delay rate, with the flight count behind each figure.")
air = db.load("airline_metrics").sort_values("delay_rate")
if not air.empty:
    left, right = st.columns(2)
    with left:
        st.markdown("**Most reliable**")
        ui.table(air.head(5), columns=["airline_name", "total_flights",
                                       "on_time_pct", "delay_rate"])
    with right:
        st.markdown("**Least reliable**")
        ui.table(air.tail(5).iloc[::-1], columns=["airline_name", "total_flights",
                                                 "on_time_pct", "delay_rate"])

st.markdown("---")
ui.section("Airports", "Best and worst performers among airports that clear the threshold.")
ui.note("Only airports with <strong>10,000+ flights</strong> are ranked. "
        "Below that, a delay rate is driven by noise rather than performance.")
ap = db.ranked("airport_metrics").sort_values("delay_rate")
if not ap.empty:
    left, right = st.columns(2)
    cols = ["airport_code", "city", "total_flights", "delay_rate"]
    with left:
        st.markdown("**Most reliable**")
        ui.table(ap.head(5), columns=cols)
    with right:
        st.markdown("**Least reliable**")
        ui.table(ap.tail(5).iloc[::-1], columns=cols)

st.markdown("---")
dist = db.load("delay_distribution")
if not dist.empty:
    order = ["early", "on_time", "15-30 min", "30-60 min", "1-2 hours", "2+ hours"]
    dist["delay_bucket"] = dist["delay_bucket"].astype("category")
    dist["delay_bucket"] = dist["delay_bucket"].cat.set_categories(
        [b for b in order if b in set(dist["delay_bucket"])])
    st.plotly_chart(charts.bar(dist.sort_values("delay_bucket"), "delay_bucket", "percentage",
                               "Distribution of arrival outcomes (% of completed flights)"),
                    width="stretch")
