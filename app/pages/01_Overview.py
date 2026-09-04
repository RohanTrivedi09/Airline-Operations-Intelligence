import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("📊 Executive Overview")

k = db.kpis()
if not k:
    st.error("No data. Run the notebooks first.")
    st.stop()

c = st.columns(5)
c[0].metric("Total flights", f"{int(k['total_flights']):,}")
c[1].metric("On-time", f"{k['on_time_pct']:.1f}%")
c[2].metric("Delayed >15 min", f"{k['delay_rate']:.1f}%")
c[3].metric("Avg dep delay", f"{k['avg_dep_delay']:.1f} min")
c[4].metric("Cancelled", f"{k['cancellation_rate']:.2f}%")

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
st.subheader("Airlines")
air = db.load("airline_metrics").sort_values("delay_rate")
if not air.empty:
    left, right = st.columns(2)
    with left:
        st.markdown("**Most reliable**")
        st.dataframe(air.head(5)[["airline_name", "total_flights", "on_time_pct", "delay_rate"]],
                     hide_index=True, width="stretch")
    with right:
        st.markdown("**Least reliable**")
        st.dataframe(air.tail(5).iloc[::-1][["airline_name", "total_flights", "on_time_pct", "delay_rate"]],
                     hide_index=True, width="stretch")

st.markdown("---")
st.subheader("Airports")
st.caption("Only airports with at least 10,000 flights are ranked — see the note on the home page.")
ap = db.ranked("airport_metrics").sort_values("delay_rate")
if not ap.empty:
    left, right = st.columns(2)
    cols = ["airport_code", "city", "total_flights", "delay_rate"]
    with left:
        st.markdown("**Most reliable**")
        st.dataframe(ap.head(5)[cols], hide_index=True, width="stretch")
    with right:
        st.markdown("**Least reliable**")
        st.dataframe(ap.tail(5).iloc[::-1][cols], hide_index=True, width="stretch")

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
