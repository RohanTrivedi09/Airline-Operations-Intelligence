"""Shared paths and Spark session factory for all notebooks.

Every notebook imports from here so Spark tuning lives in one place.

Usage from a notebook:
    import sys; sys.path.insert(0, "../src")
    from config import build_spark, PATHS
    spark = build_spark("01-loading")
"""

import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession

# Spark launches Python workers as a subprocess. Without this it picks whatever
# `python3` is first on PATH -- on this machine that is 3.14, while the driver runs
# 3.12, and Spark aborts with PYTHON_VERSION_MISMATCH the moment any Python UDF or
# createDataFrame() runs. Pin both to the interpreter that imported this module.
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PATHS = {
    "root": PROJECT_ROOT,
    # Source CSVs, as supplied.
    "dataset": PROJECT_ROOT / "Dataset",
    "flights_csv": PROJECT_ROOT / "Dataset" / "flights.csv",
    "airlines_csv": PROJECT_ROOT / "Dataset" / "airlines.csv",
    "airports_csv": PROJECT_ROOT / "Dataset" / "airports.csv",
    # Generated. Git-ignored.
    "raw": PROJECT_ROOT / "data" / "raw",          # 01: CSV -> Parquet, unmodified
    "curated": PROJECT_ROOT / "data" / "curated",  # 02: cleaned + enriched
    "marts": PROJECT_ROOT / "data" / "marts",      # 05: dashboard-ready aggregates
    "models": PROJECT_ROOT / "data" / "models",    # 06/07: fitted MLlib models
    "schema": PROJECT_ROOT / "data" / "raw" / "flights_schema.json",
}

# Tuned for this machine: 8 GB RAM, 8 cores.
# Driver does all the work in local mode, so it gets the memory. 3g leaves
# room for the OS; local[6] leaves 2 cores for everything else.
# Verified by scripts/smoke_test.py: 5.8M-row shuffle in 2.2s, no spill.
SPARK_DEFAULTS = {
    "spark.driver.memory": "3g",
    "spark.sql.shuffle.partitions": "32",
    "spark.sql.parquet.compression.codec": "snappy",
    "spark.sql.session.timeZone": "UTC",
}


def build_spark(app_suffix: str, **overrides: str) -> SparkSession:
    """Return a SparkSession tuned for this machine.

    app_suffix distinguishes runs in the Spark UI (http://localhost:4040).
    overrides let a single notebook adjust config without editing this file.
    """
    for directory in ("raw", "curated", "marts", "models"):
        PATHS[directory].mkdir(parents=True, exist_ok=True)

    builder = SparkSession.builder.appName(f"AirlineIntel-{app_suffix}").master("local[6]")
    for key, value in {**SPARK_DEFAULTS, **overrides}.items():
        builder = builder.config(key, value)

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark
