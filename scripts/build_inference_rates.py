"""Build the lookup tables the dashboard needs to score a hypothetical flight.

Notebook 06 computes smoothed historical rates from its TRAINING split, which is correct
for evaluation. At inference time there is no held-out set to protect, so these are
computed over all completed flights -- the standard practice of using every observation
available when actually predicting.

Also builds a weather climatology (airport x month means) so the prediction form can
default to typical conditions when the user does not specify weather.

Run:  .venv/bin/python scripts/build_inference_rates.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import build_spark, PATHS
from pyspark.sql import functions as F

SMOOTHING = 100
WEATHER_COLS = ["temp_c", "dewpoint_c", "wind_speed", "visibility_m", "ceiling_m",
                "precip_mm", "wx_thunderstorm", "wx_snow", "wx_rain",
                "wx_fog", "wx_freezing", "wx_haze_smoke"]


def main() -> None:
    spark = build_spark("inference-rates")

    src = PATHS["curated"] / "flights_weather.parquet"
    if not src.exists():
        src = PATHS["curated"] / "flights.parquet"
    df = spark.read.parquet(str(src)).filter(F.col("status") == "completed")

    global_rate = df.agg(F.avg("is_delayed")).first()[0]
    print(f"Source: {src.name}   global delay rate: {global_rate:.4f}")

    def smoothed(keys, out_col, name):
        out = (df.groupBy(*keys)
               .agg(F.count("*").alias("n"), F.avg("is_delayed").alias("r"))
               .withColumn(out_col,
                   (F.col("n") * F.col("r") + F.lit(SMOOTHING * global_rate))
                   / (F.col("n") + F.lit(SMOOTHING)))
               .select(*keys, out_col))
        out.coalesce(1).write.mode("overwrite").parquet(str(PATHS["marts"] / f"{name}.parquet"))
        print(f"  {name:<28}{out.count():>8,} rows")

    smoothed(["origin"], "origin_delay_rate", "rate_origin")
    smoothed(["destination"], "dest_delay_rate", "rate_destination")
    smoothed(["airline_code"], "airline_delay_rate", "rate_airline")
    smoothed(["route"], "route_delay_rate", "rate_route")
    smoothed(["origin", "sched_dep_hour"], "origin_hour_delay_rate", "rate_origin_hour")
    smoothed(["airline_code", "origin"], "airline_origin_delay_rate", "rate_airline_origin")

    if all(c in df.columns for c in WEATHER_COLS):
        clim = (df.filter(F.col("temp_c").isNotNull())
                  .groupBy("origin", "month")
                  .agg(*[F.round(F.avg(c), 4).alias(c) for c in WEATHER_COLS]))
        clim.coalesce(1).write.mode("overwrite").parquet(
            str(PATHS["marts"] / "weather_climatology.parquet"))
        print(f"  {'weather_climatology':<28}{clim.count():>8,} rows")
    else:
        print("  weather columns absent -- skipping climatology")

    # The global fallback, so the dashboard never has to hardcode it.
    spark.createDataFrame([{"global_delay_rate": float(global_rate),
                            "smoothing": SMOOTHING}]).coalesce(1) \
         .write.mode("overwrite").parquet(str(PATHS["marts"] / "inference_defaults.parquet"))
    print(f"  {'inference_defaults':<28}{1:>8,} rows")

    spark.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
