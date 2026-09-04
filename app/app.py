"""Airline Operations Intelligence Platform -- dashboard entry point.

Run:  .venv/bin/streamlit run app/app.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import db  # noqa: E402

st.set_page_config(page_title="Airline Operations Intelligence",
                   page_icon="✈️", layout="wide")

st.title("✈️ Airline Operations Intelligence Platform")
st.caption("US domestic flights, 2015 · 5,819,078 records · Big Data Analytics project")

source = db.source_name()
(st.success if source == "MongoDB" else st.warning)(f"Data source: **{source}**")

k = db.kpis()
if not k:
    st.error("No data found. Run notebooks 01-08, then `docker compose up -d`.")
    st.stop()

c = st.columns(5)
c[0].metric("Total flights", f"{int(k['total_flights']):,}")
c[1].metric("On-time", f"{k['on_time_pct']:.1f}%")
c[2].metric("Avg arrival delay", f"{k['avg_arr_delay']:.1f} min")
c[3].metric("Cancelled", f"{k['cancellation_rate']:.2f}%")
c[4].metric("Diverted", f"{k['diversion_rate']:.2f}%")

st.markdown("---")
st.markdown(
    """
### How to use this dashboard

Select a page from the sidebar.

| Page | Question it answers |
|---|---|
| **Overview** | How did the network perform overall, and how did that change through the year? |
| **Airlines** | Which carriers are most and least reliable, adjusted for how much they fly? |
| **Airports** | Which airports struggle, when do they struggle, and what type of airport are they? |
| **Routes** | Which origin→destination pairs are reliable, and which should be avoided? |
| **Delay causes** | What actually causes delays, and when do they cluster? |
| **Prediction** | What is the delay risk for a flight that has not happened yet? |

### How it works

Every number here was precomputed by Apache Spark and stored as a document. The dashboard
performs **no aggregation** — it reads a few hundred KB instead of scanning 5.8 million rows,
which is why it responds instantly.

```
CSV (565 MB) → PySpark ETL → Parquet (201 MB) → Spark aggregations
             → MongoDB (1.8 MB, 6,076 documents) → this dashboard
```

### Reading the numbers fairly

Rankings exclude very low-volume airports and routes. An airport with 76 flights can show a
44% delay rate on noise alone, so a minimum-sample threshold is applied before ranking —
sample sizes are shown throughout so you can judge for yourself.
"""
)

st.markdown("---")
st.caption(
    f"Airlines: {int(k.get('airlines', 0))} · Airports: {int(k.get('airports', 0))} · "
    f"Routes: {int(k.get('routes', 0)):,} · Data: US DOT / BTS via Kaggle"
)
