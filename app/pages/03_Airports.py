import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db, ui

st.set_page_config(page_title="Airports", page_icon=":material/location_on:", layout="wide")
ui.setup('Airport Intelligence', 'Operational profiles, rankings and drill-down')

ap = db.load("airport_metrics")
if ap.empty:
    st.error("No airport data. Run notebooks 05 and 07, then `docker compose up -d`.")
    st.stop()

mapped = ap.dropna(subset=["lat", "lon"])
clustered = mapped[mapped["cluster_id"].notna()] if "cluster_id" in mapped else mapped.iloc[0:0]

tab_map, tab_rank, tab_one = st.tabs(
    ["  Map & profiles  ", "  Rankings  ", "  Single airport  "])

# ------------------------------------------------------------------ map
with tab_map:
    # The map heading lives in page type, not inside the figure. A Plotly title sits in
    # the same band as the modebar and collides with it once the viewport narrows.
    ui.section("Airport map", "Circle size is flight volume.")
    mode = st.radio("Colour by", ["Operational cluster", "Delay rate"], horizontal=True)

    if mode == "Operational cluster" and not clustered.empty:
        fig = px.scatter_map(
            clustered, lat="lat", lon="lon", color="cluster_label",
            size="total_flights", size_max=26, hover_name="airport_name",
            zoom=3.05, center=dict(lat=39.5, lon=-98.4),
            hover_data={"airport_code": True, "delay_rate": ":.1f", "total_flights": ":,",
                        "lat": False, "lon": False},
            color_discrete_map=charts.CLUSTER_COLOURS)
        caption = ("Only airports with 10,000+ flights are clustered. Smaller airports keep "
                   "all their metrics but are not assigned a profile, because a few hundred "
                   "flights cannot support a reliable one.")
    else:
        fig = px.scatter_map(
            mapped, lat="lat", lon="lon", color="delay_rate", size="total_flights",
            size_max=26, hover_name="airport_name",
            zoom=3.05, center=dict(lat=39.5, lon=-98.4),
            color_continuous_scale="RdYlGn_r",
            hover_data={"airport_code": True, "delay_rate": ":.1f", "total_flights": ":,",
                        "lat": False, "lon": False})
        caption = "Circle size is flight volume; colour is delay rate."

    # Plotly centres on (0,0) when no centre is given, which puts a US map over Africa.
    # `zoom` and `center` must be passed to px.scatter_map directly -- setting them via
    # update_layout(map=...) is silently ignored. This bug passed the whole AppTest suite.
    fig.update_layout(
        height=560, margin=dict(l=0, r=0, t=8, b=52),
        map_style="carto-positron",
        # Legend below the map: horizontal at the top collides with the chart title, and
        # on the right the long cluster labels are clipped by the map edge.
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="left", x=0,
                    font=dict(size=11), title_text=""),
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif",
                  size=12, color="#161A22"),
        paper_bgcolor="#FFFFFF")
    st.plotly_chart(fig, width="stretch")
    st.caption(caption)

    missing = len(ap) - len(mapped)
    if missing:
        st.caption(f"{missing} airports lack coordinates and are absent from the map only — "
                   "they remain in every metric on this page.")

    prof = db.load("ml_clustering_results")
    if not prof.empty:
        ui.section("Operational profiles",
                   "K-Means groups airports by how they operate — volume, delay rate, "
                   "cancellations, peak-hour congestion and airlines served.")
        ui.table(prof.sort_values("delay_rate"))
        ui.note(
            "<strong>Scaling matters here.</strong> <code>total_flights</code> spans 50 to "
            "300,000 while rates run 0–100, so without standardisation K-Means would simply "
            "sort airports by size and rediscover nothing."
        )
    else:
        st.plotly_chart(charts.empty("No cluster profiles — run notebook 07."),
                        width="stretch")

# ------------------------------------------------------------------ rankings
with tab_rank:
    ranked = db.ranked("airport_metrics").sort_values("delay_rate")
    if ranked.empty:
        st.plotly_chart(charts.empty("No ranked airports."), width="stretch")
    else:
        ui.section("Rankings", "Airports with at least 10,000 flights only.")
        cols = ["airport_code", "airport_name", "city", "state", "total_flights",
                "avg_dep_delay", "delay_rate", "cancellation_rate", "peak_delay_hour"]
        cols = [c for c in cols if c in ranked.columns]
        left, right = st.columns(2)
        with left:
            st.markdown("**Most reliable**")
            ui.table(ranked.head(10), columns=cols)
        with right:
            st.markdown("**Least reliable**")
            ui.table(ranked.tail(10).iloc[::-1], columns=cols)
        ui.note(
            f"<strong>{len(ranked)} of {len(ap)} airports</strong> clear the 10,000-flight "
            "threshold and are ranked. Without it the worst airport in the dataset is one "
            "with 76 flights and a 44.7% delay rate — noise, not performance."
        )

# ------------------------------------------------------------------ drill-down
with tab_one:
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
        if at_airport.empty:
            st.caption(f"No airline at {code} reaches the 500-flight reporting threshold.")
        else:
            ui.section(f"Airlines operating at {code}", "500+ flights at this airport.")
            st.plotly_chart(charts.bar(at_airport, "airline_name", "delay_rate",
                                       f"Delay rate by airline at {code} (%)"),
                            width="stretch")
