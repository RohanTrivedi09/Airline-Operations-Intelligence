import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Airports", page_icon="🗺️", layout="wide")
ui.setup('Airport Intelligence', '🗺️', 'Operational profiles, rankings and drill-down')

ap = db.load("airport_metrics")
if ap.empty:
    st.error("No airport data.")
    st.stop()

mapped = ap.dropna(subset=["lat", "lon"])
clustered = mapped[mapped["cluster_id"].notna()] if "cluster_id" in mapped else mapped.iloc[0:0]

st.subheader("Airport map")
mode = st.radio("Colour by", ["Operational cluster", "Delay rate"], horizontal=True)

if mode == "Operational cluster" and not clustered.empty:
    fig = px.scatter_map(
        clustered, lat="lat", lon="lon", color="cluster_label",
        size="total_flights", size_max=26, hover_name="airport_name",
        zoom=3.05, center=dict(lat=39.5, lon=-98.4),
        hover_data={"airport_code": True, "delay_rate": ":.1f", "total_flights": ":,",
                    "lat": False, "lon": False},
        color_discrete_map=charts.CLUSTER_COLOURS,
        title="Airports by operational profile (K-Means, notebook 07)")
    st.caption("Only airports with 10,000+ flights are clustered. Smaller airports keep all "
               "their metrics but are not assigned a profile, because a few hundred flights "
               "cannot support a reliable one.")
else:
    fig = px.scatter_map(
        mapped, lat="lat", lon="lon", color="delay_rate", size="total_flights",
        size_max=26, hover_name="airport_name",
        zoom=3.05, center=dict(lat=39.5, lon=-98.4),
        color_continuous_scale="RdYlGn_r",
        hover_data={"airport_code": True, "delay_rate": ":.1f", "total_flights": ":,",
                    "lat": False, "lon": False},
        title="Airports by delay rate")

# Plotly centres on (0,0) when no centre is given, which puts a US map over Africa.
# Centre and zoom on the continental US explicitly, and lay the legend across the top
# so long cluster labels are not clipped by the map edge.
fig.update_layout(
    height=560, margin=dict(l=0, r=0, t=34, b=52),
    map_style="carto-positron",
    # Legend below the map: horizontal at the top collides with the chart title, and
    # on the right the long cluster labels are clipped by the map edge.
    legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="left", x=0,
                font=dict(size=11), title_text=""),
    font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif",
              size=12, color="#161A22"),
    paper_bgcolor="#FFFFFF")
st.plotly_chart(fig, width="stretch")

missing = len(ap) - len(mapped)
if missing:
    st.caption(f"{missing} airports lack coordinates and are absent from the map only — "
               "they remain in every metric above and below.")

st.markdown("---")
st.subheader("Operational profiles")
prof = db.load("ml_clustering_results")
if not prof.empty:
    st.caption("K-Means groups airports by how they operate — volume, delay rate, "
               "cancellations, peak-hour congestion and airlines served.")
    st.dataframe(prof.sort_values("delay_rate"), hide_index=True, width="stretch")

st.markdown("---")
st.subheader("Rankings")
st.caption("Airports with at least 10,000 flights only.")
ranked = db.ranked("airport_metrics").sort_values("delay_rate")
cols = ["airport_code", "airport_name", "city", "state", "total_flights",
        "avg_dep_delay", "delay_rate", "cancellation_rate", "peak_delay_hour"]
cols = [c for c in cols if c in ranked.columns]
left, right = st.columns(2)
left.markdown("**Most reliable**")
left.dataframe(ranked.head(10)[cols], hide_index=True, width="stretch")
right.markdown("**Least reliable**")
right.dataframe(ranked.tail(10).iloc[::-1][cols], hide_index=True, width="stretch")

st.markdown("---")
st.subheader("Single airport")
code = st.selectbox("Airport", sorted(ap["airport_code"]))
row = ap[ap["airport_code"] == code].iloc[0]
peak = (f"{int(row['peak_delay_hour']):02d}:00"
        if row.get("peak_delay_hour") == row.get("peak_delay_hour") else "n/a")
ui.kpis([
    {"label": "Flights", "value": f"{int(row['total_flights']):,}",
     "sub": f"{int(row.get('airlines_served', 0))} airlines"},
    {"label": "Delay rate", "value": f"{row['delay_rate']:.1f}%",
     "tone": ui.tone_for_delay(row["delay_rate"])},
    {"label": "Avg dep delay", "value": f"{row['avg_dep_delay']:.1f} min"},
    {"label": "Cancellations", "value": f"{row['cancellation_rate']:.2f}%"},
    {"label": "Peak delay hour", "value": peak, "sub": "worst hour by delay rate"},
])
if row.get("cluster_label"):
    st.info(f"**Operational profile:** {row['cluster_label']}")
else:
    st.warning("Below the 10,000-flight threshold, so no operational profile is assigned.")

aa = db.load("airline_airport")
if not aa.empty and "airport_code" in aa.columns:
    at_airport = aa[aa["airport_code"] == code].sort_values("delay_rate")
    if not at_airport.empty:
        st.markdown(f"**Airlines operating at {code}** (500+ flights)")
        st.plotly_chart(charts.bar(at_airport, "airline_name", "delay_rate",
                                   f"Delay rate by airline at {code} (%)"),
                        width="stretch")
