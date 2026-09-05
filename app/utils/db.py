"""Data access for the dashboard.

Reads precomputed documents from MongoDB. If MongoDB is unreachable, falls back to
the Parquet marts on disk so the dashboard still runs -- a live demo should not fail
because a container is stopped.

Nothing here aggregates. Every heavy computation happened in the Spark notebooks.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MARTS_DIR = PROJECT_ROOT / "data" / "marts"

load_dotenv(PROJECT_ROOT / ".env")


@st.cache_resource
def _mongo_db():
    """Return a live MongoDB handle, or None if unreachable."""
    try:
        import certifi
        from pymongo import MongoClient

        # tlsCAFile is required for Atlas from a python.org build on macOS: those
        # interpreters do not read the system keychain, so TLS to Atlas fails with
        # CERTIFICATE_VERIFY_FAILED. Harmless for a plain localhost connection, which
        # is not TLS at all, so it can be passed unconditionally.
        client = MongoClient(
            os.getenv("MONGO_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=1500,
            tlsCAFile=certifi.where(),
        )
        client.admin.command("ping")
        return client[os.getenv("MONGO_DB", "airline_intel")]
    except Exception:
        return None


def source_name() -> str:
    return "MongoDB" if _mongo_db() is not None else "Parquet (MongoDB unavailable)"


@st.cache_data(ttl=600)
def load(collection: str) -> pd.DataFrame:
    """Load one collection as a DataFrame, from MongoDB or the Parquet fallback."""
    db = _mongo_db()
    if db is not None:
        docs = list(db[collection].find({}, {"_id": 0}))
        if docs:
            return pd.DataFrame(docs)

    path = MARTS_DIR / f"{collection}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


def kpis() -> dict:
    df = load("overall_kpis")
    return df.iloc[0].to_dict() if not df.empty else {}


def trends(dimension: str) -> pd.DataFrame:
    df = load("time_trends")
    if df.empty:
        return df
    out = df[df["dimension"] == dimension].copy()
    if dimension in ("hourly", "day_of_week"):
        out["period_sort"] = out["period"].astype(int)
        out = out.sort_values("period_sort")
    else:
        out = out.sort_values("period")
    return out


def ranked(collection: str, min_sample_only: bool = True) -> pd.DataFrame:
    """Load a collection, optionally keeping only rows that pass the sample threshold.

    Rankings must not be driven by low-volume entities -- see notebook 04.
    """
    df = load(collection)
    if min_sample_only and "meets_min_sample" in df.columns:
        df = df[df["meets_min_sample"] == True]  # noqa: E712
    return df
