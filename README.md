# Airline Operations Intelligence Platform

Big Data Analytics project over the Kaggle 2015 US flight-delays dataset (5,819,079 records):
PySpark ETL → Spark analytics & MLlib → MongoDB serving layer → Streamlit dashboard.

Full specification: [`BDAProject_Final.md`](BDAProject_Final.md)

## Verified environment

Runs **locally** — no Colab required. Confirmed working on this machine:

| Component | Version |
|---|---|
| Java | 21.0.2 LTS |
| Python | 3.12.1 (venv at `.venv`) |
| PySpark | 4.0.0 |
| Machine | 8 GB RAM / 8 cores → `local[6]`, 3 GB driver |

Measured: 5.8M-row load + count in **7.2s**, full shuffle aggregate in **2.2s**.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "pyspark[sql]==4.0.0" pandas pyarrow ipykernel
.venv/bin/python -m ipykernel install --user --name airline-intel \
    --display-name "Python 3.12 (airline-intel)"
```

Verify the stack before running anything:

```bash
.venv/bin/python scripts/smoke_test.py     # expect: PASS
```

## Running notebooks

Open in VS Code and select kernel **"Python 3.12 (airline-intel)"**.
Spark UI is live at http://localhost:4040 while cells run.

Spark config and all paths live in [`src/config.py`](src/config.py) — one place, not ten.

## Layout

```
Dataset/          source CSVs (flights, airlines, airports)
data/raw/         01 output: Parquet, partitioned by month   [git-ignored]
data/curated/     02 output: cleaned + enriched              [git-ignored]
data/marts/       05 output: dashboard-ready aggregates      [git-ignored]
notebooks/        01-10
src/config.py     shared paths + Spark session factory
scripts/          smoke_test.py
```

## Progress

| # | Notebook | Status |
|---|---|---|
| 01 | `data_loading` — load, quality audit, raw Parquet | **Done, executed, verified** |
| 02 | `data_cleaning_etl` — 11 rules, row-count contract, curated Parquet | **Done, executed, verified** |
| 03 | `rdd_mapreduce_demo` — MapReduce, RDD internals, API benchmark | **Done, executed, verified** |
| 04 | `sparksql_demo` — views, SQL vs DataFrame equivalence, Catalyst | **Done, executed, verified** |
| 05 | `aggregations` — 8 dashboard marts, validated | **Done, executed, verified** |
| 06 | `ml_classification` — LR + Random Forest, leakage-controlled | **Done, executed, verified** |
| 07 | `ml_clustering` — K-Means airport profiles | **Done, executed, verified** |
| 08 | `mongodb_push` | Next |
| 09 | `streaming_demo` *(extension)* | — |
| 10 | `spark_concepts_doc` | — |
| — | Streamlit dashboard | — |

## Key findings from notebook 01

Measured, not assumed — these drive the ETL rules in notebook 02:

- **486,165 flights (8.4%) use DOT numeric airport codes instead of IATA — all in October.**
  A naive inner join against `airports.csv` silently drops the entire month.
- Nulls in arrival columns are **structural**: 89,884 cancelled + 15,187 diverted. Never fill with 0.
- Delay-cause columns are populated for exactly the 1,063,439 flights arriving 15+ min late.
- **17.8%** of flights are delayed >15 min → a "never delayed" model scores 82.2% accuracy
  and is worthless. Report F1, not accuracy.
- 3,731 flights were cancelled *after* departure, so `CANCELLED = 1` ≠ "never left the gate".
- Parquet conversion: 565 MB → 144 MB, with a 2.7× faster partial-column scan.

## Notebook 02 results

Curated dataset: **5,819,078 rows × 49 columns, 201 MB** at `data/curated/flights.parquet`.
**100.000% of rows retained** (the single row lost is the one known duplicate key).

### Recovering October's airport codes without an external lookup

The 486,165 October flights use DOT numeric codes that cannot join to `airports.csv`.
The mapping is reconstructed from the dataset itself:

1. `DISTANCE` is deterministic per airport pair, so the *set of distances an airport flies*
   is a fingerprint. Built from **both** departures and arrivals — one code (`10666`)
   appears only as a destination, on a single flight.
2. Fingerprints alone tie for small airports (23 DOT codes match ATL perfectly), so
   **flight volume** is added as a second signal.
3. Scores are resolved to a strict **one-to-one assignment**.
4. The result is validated against a signal it was not fitted on: each October route's
   `DISTANCE` must equal that IATA pair's distance in the other 11 months.

**Result: 307/307 codes resolved, 99.910% distance agreement (±1 mi).**
7 tiny/seasonal airports (617 flights, 0.011%) validate below 95% — documented, not hidden.

### Verification
Every stage asserts a row-count contract, and the airport join asserts zero unmatched rows.
The decisive check: October now reports 486,165 of 486,165 flights with airport metadata,
and its delay rate (12.44%) sits naturally beside September's 13.00%.

## Notebook 03 results — measured, on 5,819,078 rows

| Same query, three APIs | Time | vs RDD |
|---|---|---|
| RDD `map`/`reduceByKey` | 21.91s | 1.0× |
| DataFrame `groupBy().agg()` | 0.41s | **53×** |
| SparkSQL | 0.28s | **78×** |

All three return identical results; DataFrame and SparkSQL compile to the *same* Catalyst
plan (verified after normalising expression ids). Average delay per airline: RDD needs
manual `(sum, count)` plumbing and runs 21.9× slower than one `groupBy().agg()`.

**Iterative workload** (5 passes): 29.52s recomputing vs 12.39s cached — **2.4×**. This is
the limitation that makes classical MapReduce impractical for machine learning.

**A negative result, reported as such:** `reduceByKey` vs `groupByKey` shows only ~1.2×
across four key cardinalities (14 → 4,898 keys), not the dramatic textbook gap. In local
mode there is no network for a combiner to save, values are 1-byte integers, and PySpark
serialisation dominates. The guidance still holds on a real cluster — `groupByKey` can OOM
when one key's values exceed executor memory — but this benchmark cannot show it. See
`docs/engineering_decisions.md`.

## Notebook 04 results

**SparkSQL and the DataFrame API proven identical** — 14 airline rows asserted equal, not
eyeballed. Both compile to the same Catalyst plan (verified in notebook 03).

**`HAVING` as a bias control.** The same "worst airports" query, with and without a
minimum-sample threshold:

| Without threshold | | With `HAVING COUNT(*) >= 10000` | |
|---|---|---|---|
| GST | 44.74% on **76 flights** | LGA | 23.39% on **103,281 flights** |
| ADK | 43.30% on **97 flights** | ORD | 23.12% on **304,120 flights** |

The unfiltered ranking is noise. This implements the small-sample bias mitigation the
proposal commits to, enforced in the SQL layer.

**Catalyst optimisation, read off the physical plan:**
- `PartitionFilters: [(month = 7)]` — prunes 11 of 12 partition directories at file level
- `PushedFilters: [EqualTo(status,completed)]` — evaluated inside the Parquet reader
- `ReadSchema: 3 of 49 columns` — the other 46 are never read

One subtlety worth knowing: a **cached** relation is substituted for a file scan, which
hides all file-level pruning. The notebook clears the cache before this demonstration and
says why — otherwise the plan silently shows the wrong thing.

## Notebook 05 results — the serving layer

Eight marts written to `data/marts/`, matching the MongoDB schemas in proposal §17:

| Mart | Rows | | Mart | Rows |
|---|---|---|---|---|
| `overall_kpis` | 1 | | `time_trends` | 47 |
| `airline_metrics` | 14 | | `delay_distribution` | 6 |
| `airport_metrics` | 322 | | `delay_causes` | 5 |
| `route_metrics` | 4,706 | | `airline_airport` | 969 |

**Total mart size: 276 KB**, against 201 MB curated and 565 MB raw CSV. That ratio *is*
the serving-layer argument — the dashboard reads a few hundred KB instead of scanning
5.8M rows on every interaction.

### Headline findings

Overall: **81.39% on-time**, 18.61% delayed, 1.54% cancelled, 0.26% diverted,
avg arrival delay 4.41 min across 322 airports and 4,706 routes.

Best and worst airlines by delay rate (all 14 shown in the mart, with sample sizes):

| Rank | Airline | Flights | On-time % | Delay rate |
|---|---|---|---|---|
| 1 | Hawaiian | 76,272 | 88.67% | 11.33% |
| 2 | Alaska | 172,521 | 86.96% | 13.04% |
| 3 | Delta | 875,881 | 86.44% | 13.56% |
| 13 | Frontier | 90,836 | 73.84% | 26.16% |
| 14 | Spirit | 117,379 | 70.29% | 29.71% |

Delay causes, over the 1,063,439 flights arriving 15+ min late:

| Cause | Share of delay minutes | Avg min per late flight |
|---|---|---|
| Late aircraft | 39.84% | 23.47 |
| Carrier | 32.20% | 18.97 |
| NAS | 22.88% | 13.48 |
| Weather | 4.95% | 2.92 |
| Security | 0.13% | 0.08 |

### Validation
KPIs cross-checked against independent direct queries (all match to 0.01), and airline,
airport and route totals each reconcile to exactly 5,819,078 rows.

## Notebook 06 results — delay prediction

Trained **locally** on 4,675,637 rows; Random Forest took 134s on 8 GB, so the Colab
fallback was not needed.

| Metric | Logistic Regression | Random Forest | Baseline |
|---|---|---|---|
| Accuracy | 0.6005 | 0.6098 | **0.8139** |
| Precision | 0.2608 | 0.2678 | — |
| Recall | 0.6248 | **0.6324** | — |
| F1 | 0.3680 | **0.3763** | — |
| ROC-AUC | 0.6501 | **0.6626** | — |

**Accuracy is below the baseline, and that is the intended trade.** Class weighting
(4.373× on the minority class) sacrifices accuracy to catch delays: the Random Forest
identifies **134,596 of 212,844 delayed flights (63%)**, where an unweighted model scoring
81.4% accuracy would catch almost none. ROC-AUC 0.663 is the fair summary — the model
carries real signal, well above the 0.5 of random guessing.

Top features (Gini importance, names resolved from vector metadata):

| Feature | Importance |
|---|---|
| `sched_dep_hour` | 0.2317 |
| `route_delay_rate` | 0.1743 |
| `time_of_day=morning` | 0.1077 |
| `season=autumn` | 0.0728 |
| `airline_delay_rate` | 0.0666 |

### Method notes that matter
- **Leakage controlled in code**, not comments: a `BANNED` set (dep_delay, taxi times,
  air_time, actual times, cause columns) is asserted against the feature set before training.
- **Historical rate features are computed from the training split only**, with Bayesian
  smoothing toward the global mean, so test outcomes never leak into training features.
- **The ceiling is inherent.** Pre-departure features cannot capture the inbound aircraft
  running late (39.8% of delay minutes), day-of weather, or ATC decisions. Large
  irreducible error is the correct result here, not a modelling failure.

## Notebook 07 results — airport operational profiles

K-Means over 6 operational features, on the **80 airports** meeting the 10,000-flight
threshold. The other 242 keep every metric and receive `cluster_id = null` rather than a
noise-driven label.

k chosen at **4** (silhouette 0.351; WCSS 226.8). Silhouette alone favours k=2 (0.446),
but two clusters cannot distinguish airport types usefully — both criteria are reported so
the choice is auditable.

| Cluster | Airports | Avg flights | Delay rate | Largest members |
|---|---|---|---|---|
| High-traffic hub, elevated delays | 16 | 170,858 | 20.6% | ATL, ORD, DFW, DEN, LAX, SFO |
| High-traffic hub, well-managed | 33 | 47,141 | 17.1% | MSP, SEA, DTW, CLT, DCA |
| Smaller airport, elevated delays | 21 | 26,998 | 18.0% | MDW, MIA, DAL, HOU, IAD |
| Smaller airport, reliable | 10 | 33,525 | 12.5% | SLC, PDX, HNL, SNA, OGG |

The clusters separate cleanly on delay rate (12.5% → 20.6% across profiles) and map onto
recognisable airport types, which is what makes them usable as dashboard labels.

**Scaling is what makes this work:** `total_flights` spans 50–300,000 while rates are
0–100, so without `StandardScaler` K-Means would simply sort airports by size.
