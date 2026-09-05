"""Live streaming monitor — reads rolling metrics written by scripts/stream_consumer.py.

This is the dashboard face of the Structured Streaming demonstration in notebook 09.
Unlike every other page, the data here changes while you watch it.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

st.set_page_config(page_title="Live monitor", page_icon="📡", layout="wide")

from utils import charts, db, ui  # noqa: E402

ui.setup("Live Operations Monitor", "📡",
         "Spark Structured Streaming · rolling metrics, updated per micro-batch")


def live(collection: str) -> pd.DataFrame:
    """Read a live collection directly, bypassing the cache used elsewhere.

    Every other page reads precomputed documents that change only when a notebook runs,
    so a 10-minute cache is right. These change every few seconds.
    """
    handle = db._mongo_db()
    if handle is None:
        return pd.DataFrame()
    # Keep _id here, unlike db.load(), which projects it away. In the marts it is a
    # meaningless ObjectId; in these collections it IS the business key -- the origin
    # airport code in live_airports, the literal "totals" in live_metrics -- because
    # the consumer upserts on it to make each micro-batch idempotent. Projecting it
    # out silently removes the airport column this page charts on.
    return pd.DataFrame(list(handle[collection].find({})))


# Default OFF: an always-on rerun loop keeps a Spark-free page busy and makes the
# page untestable headlessly. The demo turns it on deliberately.
c_a, c_b = st.columns([1, 4])
auto = c_a.toggle("Auto-refresh (5s)", value=False)
if c_b.button("Refresh now"):
    st.rerun()

totals = live("live_metrics")

if totals.empty:
    ui.note(
        "<strong>The stream is not running.</strong> This page shows rolling metrics "
        "produced by a Spark Structured Streaming job; with no job running there is "
        "nothing to display — which is the correct state, not an error."
    )
    st.markdown("""
Start it in two terminals:

```bash
# terminal 1 — the streaming job
.venv/bin/python scripts/stream_consumer.py

# terminal 2 — replay historical flights as a live feed
.venv/bin/python scripts/stream_producer.py --reset --interval 5
```
""")
    ui.section("What this demonstrates",
               "Unit 2 (real-time vs batch) and Unit 5 (streaming analytics)")
    st.markdown("""
The streaming job runs **the same DataFrame aggregation** as the batch pipeline — notebook
09 asserts the two produce identical results over the same rows. What differs is *when*
the computation happens:

| | Batch (notebooks 01–08) | Streaming (this page) |
|---|---|---|
| Trigger | Manual run | Automatic on new data |
| State | None between runs | Checkpointed, survives restart |
| Latency | Minutes over 5.8M rows | Sub-second per micro-batch |
| Output | A complete answer, once | A running answer, continuously |

Each micro-batch's aggregate is written to MongoDB via `foreachBatch`, so this page reads
the same store as every other page — the streaming job simply keeps rewriting it.
""")
    st.stop()

row = totals.iloc[0].to_dict()
events = int(row.get("events", 0))
delayed = int(row.get("delayed", 0))
rate = float(row.get("delay_rate_pct", 0.0))

updated = row.get("updated_at", "")
age = ""
try:
    dt = datetime.fromisoformat(str(updated))
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    age = f"{int(secs)}s ago" if secs < 120 else f"{int(secs/60)} min ago"
except Exception:
    pass

ui.kpis([
    {"label": "Events processed", "value": f"{events:,}",
     "sub": f"last batch +{int(row.get('batch_events', 0))}"},
    {"label": "Delayed", "value": f"{delayed:,}", "sub": "15+ min late"},
    {"label": "Rolling delay rate", "value": f"{rate:.2f}%",
     "sub": "cumulative across the stream", "tone": ui.tone_for_delay(rate)},
    {"label": "Micro-batches", "value": f"{int(row.get('batch_id', 0)) + 1:,}"},
    {"label": "Last update", "value": age or "—", "sub": "stream is live" if age else ""},
])

if age and "min" in age:
    st.warning("No new events recently — the producer may have finished or stopped.")

ui.section("Airport activity", "Cumulative counts per origin, updated each micro-batch.")
airports = live("live_airports")
if not airports.empty:
    airports = airports.rename(columns={"_id": "airport"})
    airports["delay_rate_pct"] = (100 * airports["delayed"] / airports["flights"]).round(2)
    top = airports.sort_values("flights", ascending=False).head(15)

    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(
            charts.bar(top.sort_values("delay_rate_pct"), "airport", "delay_rate_pct",
                       "Delay rate by origin (streamed so far)",
                       color="delay_rate_pct", color_continuous_scale=charts.DELAY_SCALE),
            width="stretch")
    with right:
        alerts = airports[(airports.flights >= 20) & (airports.delay_rate_pct >= 30)] \
            .sort_values("delay_rate_pct", ascending=False)
        st.markdown("**Alerts** — 30%+ delayed, 20+ flights seen")
        if alerts.empty:
            st.success("No airport above the alert threshold yet.")
        else:
            ui.table(alerts, columns=["airport", "flights", "delayed", "delay_rate_pct"])
    ui.note(
        "The alert threshold needs a minimum event count for the same reason the batch "
        "rankings do: an airport with three streamed flights can show 100% delayed."
    )

ui.section("Recent events", "The tail of the most recent micro-batch.")
recent = live("live_recent")
if not recent.empty:
    cols = [c for c in ["airline_code", "origin", "destination", "sched_dep_hour",
                        "dep_delay", "arr_delay", "is_delayed"] if c in recent.columns]
    ui.table(recent, columns=cols)

if auto:
    import time
    time.sleep(5)
    st.rerun()
