"""Train a Spark-free serving model with the same features as the Spark GBT.

Why this exists
---------------
Streamlit Community Cloud has no JVM, so `data/models/best_delay_classifier` (a Spark
GBTClassificationModel) cannot be loaded there. Training stays distributed; serving does
not need to be. This is the standard train-big / serve-small split.

`HistGradientBoostingClassifier` is the same histogram-based gradient boosting algorithm
as the Spark GBT and as LightGBM, and its wheels are self-contained -- LightGBM on macOS
needs Homebrew's libomp, which is a system dependency this project should not require.

Honest caveat, also printed at the end
--------------------------------------
This model gets its own stratified split and computes its own train-split-only smoothed
rates. It is therefore *comparable to* the Spark GBT's 0.7134, not measured on the
identical rows -- Spark's `sampleBy` partitioning cannot be reproduced in pandas. With
~1.1M test rows the sampling noise on that comparison is far below the gap being reported.

Run:  .venv/bin/python scripts/export_serving_model.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import PATHS  # noqa: E402

SEED = 42
SMOOTHING = 100          # same Bayesian smoothing constant as notebook 06
WX = ["temp_c", "dewpoint_c", "wind_speed", "visibility_m", "ceiling_m", "precip_mm",
      "wx_thunderstorm", "wx_snow", "wx_rain", "wx_fog", "wx_freezing", "wx_haze_smoke"]
CATEGORICAL = ["airline_code", "time_of_day", "season"]
RATES = {
    "origin_delay_rate": ["origin"],
    "dest_delay_rate": ["destination"],
    "airline_delay_rate": ["airline_code"],
    "route_delay_rate": ["route"],
    "origin_hour_delay_rate": ["origin", "sched_dep_hour"],
    "airline_origin_delay_rate": ["airline_code", "origin"],
}
NUMERIC = (["month", "day_of_week", "sched_dep_hour", "distance", "sched_duration",
            "is_weekend_int"] + list(RATES) + WX)


def main() -> None:
    t0 = time.time()
    src = PATHS["curated"] / "flights_weather.parquet"
    cols = (["status", "is_delayed", "origin", "destination", "route", "is_weekend",
             "day_of_week", "sched_dep_hour", "distance", "sched_duration", "month"]
            + CATEGORICAL + WX)
    print(f"Reading {src.name} ...", flush=True)
    df = ds.dataset(str(src), format="parquet", partitioning="hive").to_table(
        columns=cols, filter=ds.field("status") == "completed").to_pandas()
    df = df[df["is_delayed"].notna()].reset_index(drop=True)
    df["is_weekend_int"] = df["is_weekend"].astype("int8")
    df["month"] = df["month"].astype("int16")
    y = df["is_delayed"].astype("int8").to_numpy()
    print(f"  rows {len(df):,}   positive {100*y.mean():.2f}%   ({time.time()-t0:.1f}s)")

    # -- stratified 80/20 split -------------------------------------------------
    rng = np.random.default_rng(SEED)
    is_train = np.zeros(len(df), dtype=bool)
    for cls in (0, 1):
        idx = np.flatnonzero(y == cls)
        is_train[rng.choice(idx, size=int(round(0.8 * len(idx))), replace=False)] = True
    tr, te = df[is_train], df[~is_train]
    y_tr, y_te = y[is_train], y[~is_train]
    global_rate = float(y_tr.mean())
    print(f"  train {len(tr):,}  test {len(te):,}  train positive {100*global_rate:.2f}%")

    # -- smoothed target encoding, computed on the TRAIN SPLIT ONLY -------------
    # Identical formula to notebook 06: (n*r + k*prior) / (n + k). Computing these over
    # the full frame would leak test outcomes into training features.
    lookups = {}
    for out_col, keys in RATES.items():
        g = tr.groupby(keys, observed=True)["is_delayed"].agg(["count", "mean"])
        g[out_col] = ((g["count"] * g["mean"] + SMOOTHING * global_rate)
                      / (g["count"] + SMOOTHING))
        lookups[out_col] = g[[out_col]]

    def add_rates(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        for out_col, keys in RATES.items():
            out = out.join(lookups[out_col], on=keys)
            out[out_col] = out[out_col].fillna(global_rate)
        return out

    tr, te = add_rates(tr), add_rates(te)

    # -- impute weather from TRAIN means, matching notebook 06 ------------------
    wx_means = {c: float(tr[c].mean()) for c in WX}
    for frame in (tr, te):
        for c in WX:
            frame[c] = frame[c].fillna(wx_means[c]).astype("float32")

    def design(frame: pd.DataFrame) -> pd.DataFrame:
        X = frame[NUMERIC].astype("float32").copy()
        for c in CATEGORICAL:
            X[c] = pd.Categorical(frame[c], categories=cats[c])
        return X

    cats = {c: sorted(tr[c].dropna().unique().tolist()) for c in CATEGORICAL}
    X_tr, X_te = design(tr), design(te)

    # -- train ------------------------------------------------------------------
    # Same class weighting as notebook 06: minority weighted by (1-p)/p.
    w_pos = (1 - global_rate) / global_rate
    sample_weight = np.where(y_tr == 1, w_pos, 1.0)
    print(f"\nTraining HistGradientBoosting (class weight {w_pos:.3f}x) ...", flush=True)
    t1 = time.time()
    clf = HistGradientBoostingClassifier(
        max_depth=8, max_iter=200, learning_rate=0.1, max_leaf_nodes=63,
        categorical_features=CATEGORICAL, early_stopping=True, validation_fraction=0.1,
        random_state=SEED)
    clf.fit(X_tr, y_tr, sample_weight=sample_weight)
    secs = time.time() - t1
    print(f"  fitted in {secs:.1f}s over {clf.n_iter_} boosting iterations")

    # -- evaluate ---------------------------------------------------------------
    p = clf.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, p)
    best = None
    for t in np.arange(0.25, 0.80, 0.05):
        pred = p >= t
        tp = int((pred & (y_te == 1)).sum()); fp = int((pred & (y_te == 0)).sum())
        fn = int(((~pred) & (y_te == 1)).sum()); tn = len(y_te) - tp - fp - fn
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        if best is None or f1 > best["f1"]:
            best = dict(threshold=round(float(t), 2), precision=pr, recall=rc, f1=f1,
                        accuracy=(tp + tn) / len(y_te), tp=tp, fp=fp, fn=fn, tn=tn)

    print(f"\n  ROC-AUC {auc:.4f} | F1 {best['f1']:.4f} | precision {best['precision']:.4f} "
          f"| recall {best['recall']:.4f} | threshold {best['threshold']}")

    # -- persist ----------------------------------------------------------------
    import joblib
    out_dir = PATHS["models"] / "serving"
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out_dir / "hgb_delay_classifier.joblib", compress=3)
    size_mb = (out_dir / "hgb_delay_classifier.joblib").stat().st_size / 1e6

    meta = {
        "algorithm": "sklearn HistGradientBoostingClassifier",
        "purpose": "Spark-free serving for Streamlit Community Cloud",
        "numeric_features": NUMERIC,
        "categorical_features": CATEGORICAL,
        "category_levels": cats,
        "weather_means": wx_means,
        "global_delay_rate": global_rate,
        "smoothing": SMOOTHING,
        "threshold": best["threshold"],
        "roc_auc": round(float(auc), 4),
        "f1": round(best["f1"], 4),
        "precision": round(best["precision"], 4),
        "recall": round(best["recall"], 4),
        "accuracy": round(best["accuracy"], 4),
        "confusion": {k: best[k] for k in ("tp", "fp", "fn", "tn")},
        "train_rows": int(len(tr)), "test_rows": int(len(te)),
        "train_seconds": round(secs, 1), "n_iter": int(clf.n_iter_),
        "model_size_mb": round(size_mb, 2),
        "split_note": ("Own stratified 80/20 split with train-split-only smoothed rates. "
                       "Comparable to, not measured on, the Spark GBT's exact test rows."),
    }
    (out_dir / "serving_model.json").write_text(json.dumps(meta, indent=2))

    spark_auc = 0.7134
    print(f"\n  model size {size_mb:.2f} MB  ->  {out_dir}")
    print(f"\n  Spark GBT (notebook 06) ROC-AUC {spark_auc:.4f}")
    print(f"  Serving model           ROC-AUC {auc:.4f}   ({auc-spark_auc:+.4f})")
    print(f"\nDone in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
