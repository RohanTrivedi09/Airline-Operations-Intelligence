"""Verify the local Spark stack works end-to-end before writing pipeline code.

Checks, in order:
  1. JVM launches and Spark session starts (Java 21 + Spark 4.0 compatibility)
  2. Spark can read the real flights.csv
  3. A shuffle-and-aggregate job completes under the 8 GB memory budget

Run:  .venv/bin/python scripts/smoke_test.py
"""

import time
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "Dataset"


def main() -> None:
    print("=" * 62)
    print("LOCAL SPARK SMOKE TEST")
    print("=" * 62)

    t0 = time.time()
    spark = (
        SparkSession.builder.appName("AirlineIntel-SmokeTest")
        # 8 GB machine: leave headroom for the OS. Driver does the work in local mode.
        .config("spark.driver.memory", "3g")
        .config("spark.sql.shuffle.partitions", "32")
        .master("local[6]")  # 6 of 8 cores
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    print(f"\n[1/3] Spark session      OK   ({time.time() - t0:.1f}s)")
    print(f"      Spark version      {spark.version}")
    print(f"      Master             {spark.sparkContext.master}")
    print(f"      Parallelism        {spark.sparkContext.defaultParallelism}")
    print(f"      Spark UI           {spark.sparkContext.uiWebUrl}")

    flights_csv = DATASET_DIR / "flights.csv"
    if not flights_csv.exists():
        raise SystemExit(f"ERROR: {flights_csv} not found")

    t0 = time.time()
    flights = spark.read.csv(str(flights_csv), header=True, inferSchema=True)
    n_rows = flights.count()
    print(f"\n[2/3] Read + count       OK   ({time.time() - t0:.1f}s)")
    print(f"      Rows               {n_rows:,}")
    print(f"      Columns            {len(flights.columns)}")

    # A groupBy forces a shuffle -- the operation most likely to OOM on 8 GB.
    t0 = time.time()
    top = (
        flights.filter(F.col("CANCELLED") == 0)
        .groupBy("AIRLINE")
        .agg(
            F.count("*").alias("flights"),
            F.round(F.avg("DEPARTURE_DELAY"), 2).alias("avg_dep_delay"),
        )
        .orderBy(F.desc("flights"))
    )
    rows = top.collect()
    print(f"\n[3/3] Shuffle + aggregate OK  ({time.time() - t0:.1f}s)")
    print(f"\n      {'AIRLINE':<10}{'FLIGHTS':>12}{'AVG DEP DELAY':>16}")
    print("      " + "-" * 38)
    for r in rows:
        print(f"      {r['AIRLINE']:<10}{r['flights']:>12,}{r['avg_dep_delay']:>16}")

    print("\n" + "=" * 62)
    print("PASS - local Spark stack is working. Safe to build the pipeline.")
    print("=" * 62)

    spark.stop()


if __name__ == "__main__":
    main()
