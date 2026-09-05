"""Run representative Spark jobs and hold the session open so the Spark UI can be captured.

The syllabus asks for DAG visualisation via Spark UI screenshots (Unit 4, lazy evaluation
and DAG). This script exists so those screenshots show real work on the real dataset.

It is deliberately SEPARATE from notebook 10 rather than reusing it. Notebook 10 records
benchmark timings into the documentation, and capturing screenshots means driving a browser
alongside it -- exactly the concurrent load that invalidated the scaling benchmark once
already (D5). This script measures nothing and writes nothing, so contention here cannot
corrupt a published number.

Reads `data/curated/flights.parquet`; writes nothing.

Run:  .venv/bin/python scripts/spark_ui_demo.py [seconds_to_stay_open]
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import build_spark, PATHS  # noqa: E402

from pyspark.sql import functions as F  # noqa: E402
from pyspark.storagelevel import StorageLevel  # noqa: E402

HOLD = int(sys.argv[1]) if len(sys.argv) > 1 else 420


def main() -> None:
    spark = build_spark("SparkUI-Demo")
    flights = spark.read.parquet(str(PATHS["curated"] / "flights.parquet"))
    print(f"Spark UI: {spark.sparkContext.uiWebUrl}", flush=True)

    print("\n[1] narrow transformations (no shuffle, one stage)", flush=True)
    narrow = flights.filter(F.col("status") == "completed").select("airline_code", "arr_delay")
    print(f"    rows: {narrow.count():,}", flush=True)

    print("[2] wide transformation (groupBy -> shuffle -> stage boundary)", flush=True)
    per_airline = (narrow.groupBy("airline_code")
                   .agg(F.count("*").alias("flights"),
                        F.avg("arr_delay").alias("avg_delay")))
    print(f"    airlines: {per_airline.count()}", flush=True)

    print("[3] join (Catalyst chooses broadcast vs shuffle)", flush=True)
    routes = (flights.groupBy("origin", "destination")
              .agg(F.count("*").alias("n")).filter(F.col("n") >= 1000))
    joined = routes.join(F.broadcast(per_airline), how="cross")
    print(f"    joined rows: {joined.count():,}", flush=True)

    print("[4] cache + reuse (Storage tab)", flush=True)
    hourly = (flights.filter(F.col("status") == "completed")
              .groupBy("sched_dep_hour")
              .agg(F.avg("is_delayed").alias("rate"))
              .persist(StorageLevel.MEMORY_AND_DISK))
    hourly.count()
    hourly.orderBy("sched_dep_hour").show(5, truncate=False)

    flights.createOrReplaceTempView("flights")
    spark.sql("""
        SELECT airline_code, COUNT(*) AS flights, ROUND(AVG(arr_delay), 2) AS avg_delay
        FROM flights WHERE status = 'completed'
        GROUP BY airline_code ORDER BY flights DESC
    """).show(5, truncate=False)

    print(f"\nJobs complete. Holding the UI open for {HOLD}s at "
          f"{spark.sparkContext.uiWebUrl}", flush=True)
    time.sleep(HOLD)
    spark.stop()


if __name__ == "__main__":
    main()
