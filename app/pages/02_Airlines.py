import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Airlines", page_icon=":material/flight:", layout="wide")
ui.setup('Airline Performance', 'Reliability by carrier, with sample sizes')

air = db.load("airline_metrics")
if air.empty:
    st.error("No airline data.")
    st.stop()

# Show the same names the table headers use, not the mart's column names. A control
# reading "delay_rate" asks the viewer to know the schema.
metric = st.selectbox("Rank by",
                      ["delay_rate", "on_time_pct", "avg_arr_delay",
                       "avg_dep_delay", "cancellation_rate", "total_flights"],
                      format_func=ui.label)
ascending = metric in ("delay_rate", "avg_arr_delay", "avg_dep_delay", "cancellation_rate")
ranked = air.sort_values(metric, ascending=ascending)

st.plotly_chart(
    charts.bar(ranked, "airline_name", metric, f"Airlines by {metric.replace('_',' ')}",
               color=metric, color_continuous_scale="RdYlGn" if not ascending else "RdYlGn_r"),
    width="stretch")

st.caption("Every airline is shown with its flight count, so a small carrier's score can be "
           "read in context rather than taken at face value.")
ui.table(ranked, columns=["airline_code", "airline_name", "total_flights", "on_time_pct",
                          "avg_dep_delay", "avg_arr_delay", "median_delay", "delay_rate",
                          "cancellation_rate", "routes_served"])

st.divider()
ui.section("Delay rate vs cancellation rate",
           "Bubble size is flight volume. An airline can be punctual but cancel often — "
           "these are different failure modes and worth separating.")
st.plotly_chart(
    charts.scatter(air, "delay_rate", "cancellation_rate",
                   "Delay rate vs cancellation rate",
                   size="total_flights", color="on_time_pct", hover_name="airline_name"),
    width="stretch")

st.divider()
ui.section("Compare two airlines", "Side by side on the same measures.")
c1, c2 = st.columns(2)
names = sorted(air["airline_name"])
a = c1.selectbox("Airline A", names, index=0)
b = c2.selectbox("Airline B", names, index=min(1, len(names) - 1))

ra = air[air["airline_name"] == a].iloc[0]
rb = air[air["airline_name"] == b].iloc[0]
for label, key, suffix, lower_better in [
    ("Total flights", "total_flights", "", None),
    ("On-time %", "on_time_pct", "%", False),
    ("Delay rate", "delay_rate", "%", True),
    ("Avg arrival delay", "avg_arr_delay", " min", True),
    ("Cancellation rate", "cancellation_rate", "%", True),
]:
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.write(f"**{label}**")
    va, vb = ra[key], rb[key]
    fmt = (lambda v: f"{int(v):,}") if key == "total_flights" else (lambda v: f"{v:.2f}{suffix}")
    delta = None if lower_better is None else (vb - va)
    col2.metric(a, fmt(va))
    col3.metric(b, fmt(vb), delta=None if delta is None else f"{delta:+.2f}",
                delta_color="inverse" if lower_better else "normal")
