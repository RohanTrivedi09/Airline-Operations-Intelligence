"""Replay historical flights into a watched directory, simulating a live feed.

Structured Streaming picks up each new file as a micro-batch. This is the producer
side of the demo; scripts/stream_consumer.py is the Spark job that reads it.

Run:  .venv/bin/python scripts/stream_producer.py [--interval 5] [--batches 40]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import build_spark, PATHS
from pyspark.sql import functions as F

STREAM_DIR = PATHS["root"] / "data" / "streaming"
INPUT_DIR = STREAM_DIR / "input"
STAGING = STREAM_DIR / "staging"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between batches")
    ap.add_argument("--batches", type=int, default=40, help="number of batches to emit")
    ap.add_argument("--reset", action="store_true", help="clear the stream directory first")
    args = ap.parse_args()

    if args.reset and STREAM_DIR.exists():
        shutil.rmtree(STREAM_DIR)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not any(STAGING.glob("*.csv")):
        print("Preparing replay batches (one-off)…")
        spark = build_spark("stream-producer-prep")
        src = PATHS["curated"] / "flights_weather.parquet"
        if not src.exists():
            src = PATHS["curated"] / "flights.parquet"

        day = (spark.read.parquet(str(src))
               .filter((F.col("month") == 7) & (F.col("day") == 15)
                       & (F.col("status") == "completed"))
               .select("airline_code", "airline_name", "origin", "destination",
                       "sched_dep_hour", "dep_delay", "arr_delay", "is_delayed", "distance")
               .withColumn("event_time",
                           F.to_timestamp(F.concat(
                               F.lit("2015-07-15 "),
                               F.lpad(F.col("sched_dep_hour").cast("string"), 2, "0"),
                               F.lit(":00:00")))))
        day.repartition(args.batches).write.mode("overwrite") \
           .option("header", True).csv(str(STAGING))
        spark.stop()

    files = sorted(STAGING.glob("*.csv"))
    print(f"Emitting {min(args.batches, len(files))} batches every {args.interval}s")
    print(f"Watched directory: {INPUT_DIR}")
    print("Ctrl-C to stop.\n")

    try:
        for i, src in enumerate(files[:args.batches], start=1):
            shutil.copy(src, INPUT_DIR / f"batch_{int(time.time())}_{i:03d}.csv")
            print(f"  emitted batch {i}/{min(args.batches, len(files))}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nProducer stopped.")


if __name__ == "__main__":
    main()
