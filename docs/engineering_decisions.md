# Engineering Decisions & Known Limitations

A record of approaches tried and rejected, defects caught, and limitations accepted.
Feeds Sections 18 (Ethics/Bias), 21 (Risks) and 22 (Evaluation) of the project report.

---

## D1 — Recovering October's airport codes

### Problem
486,165 flights (8.4%) in October 2015 store `ORIGIN_AIRPORT`/`DESTINATION_AIRPORT` as
5-digit DOT codes instead of 3-letter IATA. `airports.csv` is IATA-keyed. An inner join
drops the entire month **without raising an error** — the pipeline "succeeds" and every
airport, route and monthly metric is silently wrong.

This is the canonical big-data failure mode: not a crash, but confidently incorrect output.

### Approach 1 — flight-number identity (REJECTED)
**Hypothesis:** a given `(AIRLINE, FLIGHT_NUMBER)` flies a stable route all year, so the
11 clean months reveal what each October numeric code means.

**Measured result:** mean confidence **0.54**; 259 of 306 codes below 90%; DFW claimed by
**19** different DOT codes, ORD by 16.

**Why it failed:** a flight number identifies a multi-leg *itinerary*, not a single leg.
`AA803` departs several different airports in one day, so origin is not a function of
flight number. The hypothesis was wrong about the domain, not merely imprecise.

### Approach 2 — distance fingerprint + volume (ACCEPTED)
`DISTANCE` is deterministic per airport pair, so the *set* of distances an airport flies
is a fingerprint of that airport.

1. Fingerprint every airport by the distances it flies, counting **both** departures and
   arrivals (see D2).
2. Fingerprints alone tie for small airports — 23 DOT codes match ATL's set perfectly,
   because a 1-route airport's single distance matches many candidates. **Flight volume**
   is added as a second signal: October volume should be ≈ 1/11 of the other months'.
3. `score = 0.6 × containment + 0.4 × volume_similarity`, resolved to a strict
   **one-to-one assignment** (two DOT codes cannot be the same airport).
4. **Validated against a signal it was not fitted on:** after substitution, each October
   route's `DISTANCE` must equal that IATA pair's distance in the clean months.

**Measured result: 307/307 codes resolved, 99.910% distance agreement (±1 mile).**

A ±1 tolerance is allowed because the source rounds inconsistently — ORD→CLE appears as
both 315 and 316 miles. That is a source-data quirk, confirmed by the fact that the
discrepancies are all off-by-one and concentrated on correctly-mapped hub routes.

### Why not a hardcoded lookup table
A published DOT→IATA table exists. It was deliberately not used: deriving the mapping from
the data demonstrates the analytical work, and — more importantly — the derivation comes
with an **independent validation step**, whereas a pasted table would be trusted blindly.

---

## D2 — Defect: airport described by departures only

**Caught by:** the assertion `assert miss_o == 0 and miss_d == 0` in notebook 02 §8.

The first implementation fingerprinted airports using `ORIGIN_AIRPORT` only. One code,
`10666`, appears in October **exclusively as a destination**, on a single flight
(AS437, 31 Oct, from SEA, 93 mi). It therefore received no mapping, and the airport join
produced a null — one row of 5.8 million.

**Fix:** `airport_signature()` unions the origin and destination roles before aggregating.

**The lesson worth reporting:** the contract caught a **single row** out of 5,819,079.
Without it, the run would have completed normally and one flight would have been quietly
excluded from all destination metrics. Assertions are what make silent loss impossible;
eyeballing output is not.

---

## D3 — Defect: Spark workers on the wrong Python

Spark launches Python workers as subprocesses, choosing whatever `python3` appears first
on `PATH` — here system **3.14**, while the driver runs **3.12**. Spark aborts with
`PYTHON_VERSION_MISMATCH`.

It stayed hidden through all of notebook 01 because pure Spark-SQL operations never start
a Python worker. It surfaced only at the first `createDataFrame()` call.

**Fix:** `src/config.py` pins `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` to
`sys.executable` at import time, so every notebook inherits it. Had this not been caught
here, it would have appeared later and less legibly inside MLlib training.

---

## L1 — Limitation: low-confidence airport mappings

7 airports validate below 95% against the route-distance check, covering
**617 flights = 0.011%** of the dataset.

| Cause | Explanation |
|---|---|
| Seasonal service | Ski/leisure airports (EGE, ASE, HDN, JAC) barely operate in October, so volume similarity is a weak signal and their distance sets are tiny |
| Very low traffic | BGM (27 flights), BGR, CDV — a 1–2 route airport has an almost uninformative fingerprint |
| Routes absent from clean months | A route flown only in October has no reference distance, so it cannot be validated either way |

**Decision:** accepted and documented rather than dropped. 0.011% cannot move any
aggregate metric materially, and dropping the rows would itself introduce bias against
small airports — the same small-sample bias the project report already commits to
avoiding in rankings.

**Where it matters:** these airports fall below the minimum-sample threshold used for
rankings anyway, so no published metric depends on them.

---

## L2 — Limitations inherited from the dataset

| Limitation | Impact |
|---|---|
| Single year (2015) | Seasonal patterns may not generalise. Not usable for booking decisions |
| US domestic only | No international operations |
| Self-reported delay causes | Airlines report their own carrier/weather/NAS attribution — potential bias |
| 3 airports lack coordinates (ECP, PBG, UST) | 5,008 flights (0.086%) retained in all metrics, excluded from the map only |
| Class imbalance: 18.61% delayed | Accuracy is misleading; F1, precision, recall and a baseline comparison are mandatory |

---

## D4 — Defect: `mode("overwrite")` onto a path being read

Notebook 07 reads `airport_metrics.parquet`, adds `cluster_id`/`cluster_label`, and writes
the result back to the same path. Spark rejects this — the output path is still in the
DataFrame's lineage — but **`mode("overwrite")` deletes the target directory before the
job fails**. The mart was destroyed and the next run could not read its own input.

**Recovery:** re-run notebook 05, which regenerates every mart deterministically. No data
was lost permanently, which is itself the argument for keeping each stage reproducible
from the stage before it.

**Fix:** write to a temporary directory, then swap:

```python
enriched.coalesce(1).write.mode("overwrite").parquet(str(tmp_path))
shutil.rmtree(final_path)
shutil.move(str(tmp_path), str(final_path))
```

**The lesson worth reporting:** `overwrite` is not atomic. A failure between "delete
target" and "write output" leaves no data at all. Any pipeline stage that updates a
dataset in place needs the temp-then-swap pattern, or it can destroy the input it depends on.
