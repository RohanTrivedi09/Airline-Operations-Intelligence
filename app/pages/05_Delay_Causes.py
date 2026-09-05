import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Delay causes", page_icon="🔍", layout="wide")
ui.setup('Delay Causes & Patterns', '🔍', 'What causes delays, and when')

# Three separate questions -- what causes delay, when it happens, how long it lasts.
# As one scroll they read as an undifferentiated wall; as tabs each keeps its own framing.
tab_cause, tab_when, tab_long = st.tabs(
    ["  Causes  ", "  Timing  ", "  Duration  "])

# ------------------------------------------------------------------ causes
with tab_cause:
    causes = db.load("delay_causes")
    if causes.empty:
        st.plotly_chart(charts.empty("No cause data — run notebook 05."), width="stretch")
    else:
        ui.section("What causes delay minutes",
                   "Measured over flights arriving 15+ minutes late — the only flights for "
                   "which the DOT attributes a cause. Averaging over all flights would "
                   "divide by the wrong denominator.")
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
        ui.table(causes.sort_values("total_minutes", ascending=False))
        st.info(
            "**Late aircraft is the largest single cause** — a delay earlier in the day "
            "propagating to later flights of the same aircraft. It is also why delay risk "
            "compounds through the operating day, which the **Timing** tab shows directly. "
            "Notebook 12 measures the propagation: when the inbound aircraft lands 60–120 "
            "minutes late, the next flight is delayed **87.3%** of the time, against a "
            "network base of 18.6%."
        )
        ui.note(
            "These are <strong>self-reported</strong> attributions. Carriers assign their own "
            "carrier/weather/NAS split, so the boundary between 'carrier' and 'NAS' reflects "
            "reporting incentives as well as operations."
        )

# ------------------------------------------------------------------ timing
with tab_when:
    hourly = db.trends("hourly")
    if hourly.empty:
        st.plotly_chart(charts.empty("No trend data — run notebook 05."), width="stretch")
    else:
        ui.section("By hour of scheduled departure",
                   "Delay risk compounds through the operating day and resets overnight.")
        st.plotly_chart(charts.bar(hourly, "period", "delay_rate",
                                   "Delay rate by scheduled departure hour (%)",
                                   color="delay_rate", color_continuous_scale="RdYlGn_r"),
                        width="stretch")

    c1, c2 = st.columns(2)
    dow = db.trends("day_of_week")
    with c1:
        if dow.empty:
            st.plotly_chart(charts.empty("No day-of-week data."), width="stretch")
        else:
            names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
            dow = dow.copy()
            dow["day"] = dow["period"].astype(int).map(names)
            st.plotly_chart(
                charts.bar(dow, "day", "delay_rate", "Delay rate by day of week (%)"),
                width="stretch")

    seasonal = db.trends("seasonal")
    with c2:
        if seasonal.empty:
            st.plotly_chart(charts.empty("No seasonal data."), width="stretch")
        else:
            st.plotly_chart(
                charts.bar(seasonal, "period", "delay_rate", "Delay rate by season (%)"),
                width="stretch")

    monthly = db.trends("monthly")
    if not monthly.empty:
        ui.section("Across the year")
        st.plotly_chart(charts.line(monthly, "period", ["delay_rate", "cancellation_rate"],
                                    "Delay and cancellation rate by month (%)"),
                        width="stretch")

# ------------------------------------------------------------------ duration
with tab_long:
    dist = db.load("delay_distribution")
    if dist.empty:
        st.plotly_chart(charts.empty("No distribution data — run notebook 05."),
                        width="stretch")
    else:
        ui.section("How long are the delays?",
                   "A 15-minute threshold treats a 16-minute delay and a 6-hour delay as "
                   "the same event. This is the distribution behind that binary.")
        order = ["early", "on_time", "15-30 min", "30-60 min", "1-2 hours", "2+ hours"]
        present = [b for b in order if b in set(dist["delay_bucket"])]
        dist = dist.set_index("delay_bucket").loc[present].reset_index()
        st.plotly_chart(charts.bar(dist, "delay_bucket", "percentage",
                                   "Arrival outcome distribution (% of completed flights)"),
                        width="stretch")
        ui.table(dist)
