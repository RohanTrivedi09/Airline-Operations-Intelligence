"""Spark Structured Streaming job: read the replayed feed, write rolling metrics to MongoDB.

Uses foreachBatch to land each micro-batch's aggregate in the same store the dashboard
already reads, so page 7 needs no new data path.

Run:  .venv/bin/python scripts/stream_consumer.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import build_spark, PATHS
from dotenv import load_dotenv
from pymongo import MongoClient
from pyspark.sql import functions as F
from pyspark.sql.types import (IntegerType, StringType, StructField, StructType,
                               TimestampType)

STREAM_DIR = PATHS["root"] / "data" / "streaming"
INPUT_DIR = STREAM_DIR / "input"
CKPT = STREAM_DIR / "checkpoint_live"

SCHEMA = StructType([
    StructField("airline_code", StringType()),
    StructField("airline_name", StringType()),
    StructField("origin", StringType()),
    StructField("destination", StringType()),
    StructField("sched_dep_hour", IntegerType()),
    StructField("dep_delay", IntegerType()),
    StructField("arr_delay", IntegerType()),
    StructField("is_delayed", IntegerType()),
    StructField("distance", IntegerType()),
    StructField("event_time", TimestampType()),
])


def main() -> None:
    load_dotenv(PATHS["root"] / ".env")
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                         serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[os.getenv("MONGO_DB", "airline_intel")]

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    CKPT.mkdir(parents=True, exist_ok=True)

    spark = build_spark("stream-consumer")
    stream = (spark.readStream.schema(SCHEMA).option("header", True)
              .option("maxFilesPerTrigger", 1).csv(str(INPUT_DIR)))

    def publish(batch_df, batch_id: int) -> None:
        """Land one micro-batch's aggregates in MongoDB.

        Cumulative totals are kept in Mongo rather than in Spark state, so the dashboard
        sees a running figure and the job can restart without losing the display.
        """
        if batch_df.isEmpty():
            return
        batch_df = batch_df.cache()
        n = batch_df.count()
        delayed = batch_df.filter(F.col("is_delayed") == 1).count()

        prev = db.live_metrics.find_one({"_id": "totals"}) or {"events": 0, "delayed": 0}
        events = prev["events"] + n
        total_delayed = prev["delayed"] + delayed

        db.live_metrics.replace_one(
            {"_id": "totals"},
            {"_id": "totals", "events": events, "delayed": total_delayed,
             "delay_rate_pct": round(100.0 * total_delayed / events, 2) if events else 0.0,
             "batch_id": batch_id, "batch_events": n,
             "updated_at": datetime.now(timezone.utc).isoformat()},
            upsert=True)

        # Per-airport rolling counts, for the alert table.
        rows = (batch_df.groupBy("origin")
                .agg(F.count("*").alias("flights"),
                     F.sum("is_delayed").alias("delayed"))
                .collect())
        for r in rows:
            db.live_airports.update_one(
                {"_id": r["origin"]},
                {"$inc": {"flights": r["flights"], "delayed": r["delayed"]},
                 "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True)

        # A short tail of recent events, so the page can show something concrete.
        recent = [r.asDict() for r in batch_df.limit(15).collect()]
        for d in recent:
            d["event_time"] = str(d.get("event_time"))
        db.live_recent.delete_many({})
        if recent:
            db.live_recent.insert_many(recent)

        print(f"  batch {batch_id}: +{n} events  (total {events:,}, "
              f"{100*total_delayed/events:.2f}% delayed)")
        batch_df.unpersist()

    # Reset the display counters so a fresh run starts from zero.
    db.live_metrics.delete_many({})
    db.live_airports.delete_many({})
    db.live_recent.delete_many({})

    query = (stream.writeStream.foreachBatch(publish)
             .option("checkpointLocation", str(CKPT))
             .outputMode("append").start())

    print(f"Consumer running. Watching {INPUT_DIR}")
    print("Start the producer in another terminal, then open the Live Monitor page.")
    print("Ctrl-C to stop.\n")
    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        query.stop()
        print("\nConsumer stopped.")
    finally:
        client.close()
        spark.stop()


if __name__ == "__main__":
    main()
