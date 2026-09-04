import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import charts, db

st.set_page_config(page_title="Routes", page_icon="🛣️", layout="wide")
st.title("🛣️ Route Intelligence")

routes = db.load("route_metrics")
if routes.empty:
    st.error("No route data.")
    st.stop()

eligible = db.ranked("route_metrics")
st.caption(f"{len(routes):,} routes in total; {len(eligible):,} have at least 1,000 flights "
           "and are eligible for ranking.")

st.subheader("Look up a route")
c1, c2 = st.columns(2)
origins = sorted(routes["origin"].unique())
o = c1.selectbox("Origin", origins, index=origins.index("LAX") if "LAX" in origins else 0)
dests = sorted(routes[routes["origin"] == o]["destination"].unique())
d = c2.selectbox("Destination", dests)

match = routes[(routes["origin"] == o) & (routes["destination"] == d)]
if match.empty:
    st.warning("No flights on that route in 2015.")
else:
    r = match.iloc[0]
    c = st.columns(5)
    c[0].metric("Flights", f"{int(r['total_flights']):,}")
    c[1].metric("Avg delay", f"{r['avg_delay']:.1f} min")
    c[2].metric("Delay rate", f"{r['delay_rate']:.1f}%")
    c[3].metric("Cancellations", f"{r['cancellation_rate']:.2f}%")
    c[4].metric("Distance", f"{int(r['distance']):,} mi")
    if r.get("meets_min_sample"):
        st.success(f"Reliability rank **{int(r['reliability_rank'])}** of {len(eligible):,} "
                   "ranked routes (1 = most reliable).")
    else:
        st.warning(f"Only {int(r['total_flights']):,} flights — below the 1,000-flight "
                   "threshold, so this route is not ranked. Treat its rates as indicative.")

st.markdown("---")
left, right = st.columns(2)
cols = ["route", "total_flights", "avg_delay", "delay_rate", "cancellation_rate"]
left.subheader("Most reliable")
left.dataframe(eligible.sort_values("delay_rate").head(15)[cols],
               hide_index=True, width="stretch")
right.subheader("Least reliable")
right.dataframe(eligible.sort_values("delay_rate", ascending=False).head(15)[cols],
                hide_index=True, width="stretch")

st.markdown("---")
st.subheader("Volume vs reliability")
st.caption("Each point is a route. Busy routes cluster toward the network average; extreme "
           "delay rates occur mostly on thin routes, which is exactly why the ranking "
           "threshold exists.")
st.plotly_chart(
    charts.scatter(eligible, "total_flights", "delay_rate",
                   "Route volume vs delay rate", color="avg_delay",
                   hover_name="route", color_continuous_scale="RdYlGn_r"),
    width="stretch")

st.markdown("---")
st.subheader("Busiest routes")
st.dataframe(routes.sort_values("total_flights", ascending=False).head(20)[cols],
             hide_index=True, width="stretch")
