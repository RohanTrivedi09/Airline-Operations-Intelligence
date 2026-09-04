import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Delay causes", page_icon="🔍", layout="wide")
ui.setup('Delay Causes & Patterns', '🔍', 'What causes delays, and when')

causes = db.load("delay_causes")
if not causes.empty:
    st.subheader("What causes delay minutes")
    st.caption("Measured over flights arriving 15+ minutes late — the only flights for which "
               "the DOT attributes a cause. Averaging over all flights would divide by the "
               "wrong denominator.")
    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(
            charts.bar(causes.sort_values("pct_of_delay_minutes", ascending=False),
                       "cause", "pct_of_delay_minutes",
                       "Share of total delay minutes (%)"),
            width="stretch")
    with right:
        fig = px.pie(causes, values="total_minutes", names="cause", hole=0.45,
                     title="Delay minutes by cause")
        st.plotly_chart(charts.style(fig), width="stretch")
    st.dataframe(causes.sort_values("total_minutes", ascending=False),
                 hide_index=True, width="stretch")
    st.info("**Late aircraft is the largest single cause** — a delay earlier in the day "
            "propagating to later flights of the same aircraft. This is also why delay risk "
            "rises through the day, visible in the hourly chart below.")

st.markdown("---")
st.subheader("When do delays happen?")

hourly = db.trends("hourly")
if not hourly.empty:
    st.plotly_chart(charts.bar(hourly, "period", "delay_rate",
                               "Delay rate by scheduled departure hour (%)",
                               color="delay_rate", color_continuous_scale="RdYlGn_r"),
                    width="stretch")
    st.caption("Delay risk compounds through the operating day and resets overnight.")

c1, c2 = st.columns(2)
dow = db.trends("day_of_week")
if not dow.empty:
    names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    dow = dow.copy()
    dow["day"] = dow["period"].astype(int).map(names)
    c1.plotly_chart(charts.bar(dow, "day", "delay_rate", "Delay rate by day of week (%)"),
                    width="stretch")

seasonal = db.trends("seasonal")
if not seasonal.empty:
    c2.plotly_chart(charts.bar(seasonal, "period", "delay_rate", "Delay rate by season (%)"),
                    width="stretch")

st.markdown("---")
monthly = db.trends("monthly")
if not monthly.empty:
    st.plotly_chart(charts.line(monthly, "period", ["delay_rate", "cancellation_rate"],
                                "Delay and cancellation rate by month (%)"),
                    width="stretch")

dist = db.load("delay_distribution")
if not dist.empty:
    st.markdown("---")
    st.subheader("How long are the delays?")
    order = ["early", "on_time", "15-30 min", "30-60 min", "1-2 hours", "2+ hours"]
    present = [b for b in order if b in set(dist["delay_bucket"])]
    dist = dist.set_index("delay_bucket").loc[present].reset_index()
    st.plotly_chart(charts.bar(dist, "delay_bucket", "percentage",
                               "Arrival outcome distribution (% of completed flights)"),
                    width="stretch")
    st.dataframe(dist, hide_index=True, width="stretch")
