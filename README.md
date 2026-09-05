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
data/weather/     NOAA ISD hourly observations                [git-ignored]
notebooks/        01-12
app/              Streamlit dashboard (Home + 7 pages)
docs/             report, data dictionary, NoSQL, decisions, testing
src/config.py     shared paths + Spark session factory
scripts/          smoke_test, fetch_weather, build_inference_rates, stream_producer/consumer
```

## Progress

| # | Notebook | Status |
|---|---|---|
| 01 | `data_loading` — load, quality audit, raw Parquet | **Done, executed, verified** |
| 02 | `data_cleaning_etl` — 11 rules, row-count contract, curated Parquet | **Done, executed, verified** |
| 03 | `rdd_mapreduce_demo` — MapReduce, RDD internals, API benchmark | **Done, executed, verified** |
| 04 | `sparksql_demo` — views, SQL vs DataFrame equivalence, Catalyst | **Done, executed, verified** |
| 05 | `aggregations` — 8 dashboard marts, validated | **Done, executed, verified** |
| 06 | `ml_classification` — 8-step ablation, LR → tuned GBT, leakage-controlled | **Done, executed, verified** |
| 07 | `ml_clustering` — K-Means airport profiles | **Done, executed, verified** |
| 08 | `mongodb_push` — 10 collections, indexed | **Done, executed, verified** |
| 09 | `streaming_demo` *(extension)* — Structured Streaming | **Done, executed, verified** |
| 10 | `spark_concepts_doc` — architecture, DAG, fault tolerance, scaling | **Done, executed, verified** |
| 11 | `weather_enrichment` *(extension)* — NOAA ISD join, METAR text parsing | **Done, executed, verified** |
| 12 | `aircraft_rotation` *(extension)* — delay propagation, planning vs day-of | **Done, executed, verified** |
| — | Streamlit dashboard — 7 pages | **Done, all pages executed and verified** |
| — | Documentation — report, data dictionary, NoSQL, decisions, testing | **Done** |

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

## Notebook 06 results — delay prediction, as an ablation study

The notebook is not a single model. It changes **one thing at a time** on the same
held-out split (train 4,571,843 / test 1,142,165, positive rate 18.62%) so every gain is
attributable to a named cause, and reports the steps that gained nothing.

| Step | ROC-AUC | F1 | Δ AUC |
|---|---|---|---|
| 0. Logistic Regression | 0.6503 | 0.3678 | — |
| 1. Random Forest | 0.6626 | 0.3765 | +0.0123 |
| 2. + tuned threshold | 0.6626 | 0.3765 | **+0.0000** |
| 3. + weather features | 0.6771 | 0.3849 | +0.0145 |
| 4. + interaction features | 0.6811 | 0.3874 | +0.0040 |
| 5. Gradient-Boosted Trees | 0.6976 | 0.4008 | +0.0165 |
| **6. GBT, tuned** | **0.7134** | **0.4165** | +0.0158 |
| 7. *Temporal split* | *0.6580* | *0.3389* | *honesty check* |

**ROC-AUC 0.6626 → 0.7134, F1 0.3765 → 0.4165.** Step 6 is the deployed model
(`maxDepth` 8, `maxIter` 80, decision threshold 0.55).

**Step 2 is a null result, kept in the table.** Threshold tuning gained exactly nothing on
the weighted Random Forest, because class weighting had already moved the F1 optimum to
0.50. It earns its place two steps later — GBT's optimum is 0.55.

**Accuracy below the 81.39% majority-class baseline is the intended trade.** A model that
predicts "on time" every time scores 81.39% and catches no delays. The tuned GBT reaches
71.56% accuracy while identifying **115,922 of 212,152 delayed flights (54.6%)** at 33.65%
precision. ROC-AUC is the fair summary, and 0.7134 is well clear of the 0.5 of guessing.

Top features (GBT importance, names resolved from vector metadata, not hand-listed):

| Feature | Importance |
|---|---|
| `origin_hour_delay_rate` | 0.1063 |
| `month` | 0.0894 |
| `origin_delay_rate` | 0.0756 |
| `dewpoint_c` | 0.0731 |
| `temp_c` | 0.0677 |
| `day_of_week` | 0.0624 |
| `ceiling_m` | 0.0567 |

Weather accounts for **28.5%** of total importance across all its columns.

### Method notes that matter
- **Leakage controlled in code**, not comments: a `BANNED` set of 18 columns (`dep_delay`,
  taxi times, `air_time`, actual times, the five cause columns) is asserted against the
  feature set before every fit.
- **Historical rate features are computed from the training split only**, with Bayesian
  smoothing toward the global mean, so test outcomes never leak into training features.
- **The random split flatters the model.** Training on Jan–Sep and testing Oct–Dec drops
  ROC-AUC to **0.6580** — partly because the delay rate itself shifts from 19.45% to 16.07%
  across that boundary. Step 7 exists so the headline number is read with that caveat.
- **The remaining ceiling is structural, and notebook 12 measures it.** Pre-departure
  features cannot observe the inbound aircraft running late — 39.84% of all delay minutes.
  That is not a modelling failure; it is information the planning problem does not have.

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

## Notebook 08 results — MongoDB serving layer

```bash
docker compose up -d      # mongo:7 on localhost:27017
```

10 collections, **6,076 documents**, 1.76 MB data + 284 KB indexes. Every collection
verified to match its source mart row-for-row.

**Indexing, measured with `explain()`:**

| | Docs examined | Stage |
|---|---|---|
| Before index | 4,706 | `COLLSCAN` |
| After index | 1 | `IXSCAN` |

Every dashboard query runs in **under 2 ms**:

| Query | Results | Time |
|---|---|---|
| Overview KPI cards | 1 | 0.3 ms |
| Airline ranking | 14 | 0.5 ms |
| Airport map (clustered) | 80 | 1.3 ms |
| Route lookup LAX→SFO | 1 | 0.3 ms |

Note the container image is **1.13 GB** (`docker rmi mongo:7` to remove); the data itself
is under 2 MB.

## Dashboard

```bash
docker compose up -d                       # MongoDB serving layer
.venv/bin/streamlit run app/Home.py         # http://localhost:8501
```

Seven pages, all verified headlessly with `streamlit.testing.AppTest` — every page
executes with zero exceptions:

| Page | Question it answers |
|---|---|
| Overview | Network performance and how it moved through the year |
| Airlines | Which carriers are reliable, with sample sizes and a two-airline comparison |
| Airports | Map coloured by K-Means cluster or delay rate, rankings, per-airport drill-down |
| Routes | Origin→destination lookup, most/least reliable, volume vs reliability |
| Delay causes | Cause breakdown, hour/day/season patterns, delay duration distribution |
| Prediction | Delay risk for a hypothetical flight, from the saved tuned GBT + weather conditions |
| Live Monitor | Rolling metrics off a running Structured Streaming job, with an explicit idle state |

**The dashboard performs no aggregation.** It reads precomputed documents — a few hundred
KB instead of 5.8M rows — which is why every page is instant.

**It also survives MongoDB being down.** `app/utils/db.py` falls back to the Parquet marts
and the home page states which source is live. Verified by stopping the container mid-test:
all pages still rendered.

The prediction page scores with the **exported serving model** (`scripts/export_serving_model.py`)
at its saved decision threshold of 0.55, against the 18.62% network baseline. Verified end
to end: LAX→JFK, July, 17:00 departure, typical weather → **40.7% delay probability**.

The serving model exists because Streamlit Cloud has no JVM. It reaches **ROC-AUC 0.7149**
against the Spark GBT's **0.7134** on an equivalent split — the same model in every way that
matters, and the page shows both numbers so the claim is checkable. Training stays
distributed; serving does not need to be (D6). Historical rate features
for an unseen hypothetical flight come from `inference_defaults` and the `rate_*` marts, so
inference uses exactly the training-split statistics — never a rate recomputed over the
test data.

## Notebooks 09–12

### 09 — Structured Streaming `[Extension]`

Replays one day (16,989 flights) through a file source in 6 micro-batches. State
accumulates correctly across batches (2,832 → 16,989), and the final streaming result is
**asserted identical to the batch result** — the same DataFrame code, two execution modes.

Also demonstrates windowed aggregation over event time with a watermark, and shows the
checkpoint contents (`offsets`, `commits`, `state`, `sources`) that give exactly-once
recovery.

Stated honestly in the notebook: a file source on one machine is not Kafka. The
*programming model* is identical, but partitioned consumption, replay from offsets and
back-pressure are not exercised.

### 10 — Spark concepts reference

Every Unit 4 claim demonstrated on the real dataset rather than asserted:

| Concept | Measured |
|---|---|
| Lazy evaluation | 5 transformations 0.29s → `collect()` 1.22s |
| Narrow vs wide | 0.19s → 0.41s once a shuffle is introduced |
| Partitioning | 24 partitions 0.99s vs 200 partitions 1.93s (scheduling overhead) |
| Caching a shuffled aggregate | 1.60s → 0.22s (**7.2×**) |
| Fault tolerance | Cache destroyed, result **recomputed from lineage** and asserted identical |

The fault-tolerance section does not describe lineage — it destroys every cached partition
and rebuilds the result, then asserts equality with the pre-loss answer.

It also measures **weak scaling** at 25/50/75/100% of the data. An earlier run of this
section reported a memory wall that turned out to be CPU contention from a concurrent job;
the finding was retracted and the correction is written up as D5 in
[`docs/engineering_decisions.md`](docs/engineering_decisions.md).

### 11 — NOAA weather enrichment `[Extension]`

Joins **real external weather** to the flight record — the second data source the proposal
asks for, and the only unstructured text in the project.

| Measurement | Result |
|---|---|
| Airports matched to NOAA ISD stations | **60** (57 by ICAO `K`+IATA, 3 by nearest-neighbour) |
| Flights covered | **4,924,097 — 84.6%** of the dataset |
| Raw ISD downloaded | 424 MB of hourly global-hourly CSVs |
| Curated output | `flights_weather.parquet`, 61 columns |

The three ICAO misses are **HNL, SJU and OGG** — Hawaii and Puerto Rico use the `PH`/`TJ`
prefixes, not `K`, so the `K`+IATA rule cannot work there by construction. A haversine
fallback resolves all three to within 1.2 km.

Two parsing hazards handled explicitly:

- **ISD sentinel values.** Missing temperature is encoded as `+9999`, not null. Dividing it
  by 10 yields a plausible-looking 999.9 °C that would silently poison every downstream
  mean. Each composite field is parsed component-wise and its sentinel mapped to `NULL`.
- **Schema drift.** ISD files carry 82–104 columns depending on station. Reading the
  directory as one glob fails; the notebook reads per-file and unions by name.

**Unstructured text:** the `metar_text` field is free-form aviation weather
(`METAR KMIA 010053Z 33005KT 10SM BKN049 24/19 A3018 RMK AO2 SLP219`). Six phenomena
(thunderstorm, snow, rain, fog, freezing, haze/smoke) are extracted by regex into boolean
features that feed the model — with negative lookbehinds so `FZRA` is not double-counted as
rain and `-SN` is caught alongside `SN`.

Weather earned **+0.0145 ROC-AUC** in the ablation and carries **28.5%** of final feature
importance.

### 12 — Aircraft rotation: delay propagation `[Extension]`

Notebook 05 measured that **late aircraft is the largest single cause of delay minutes
(39.84%)** — bigger than carrier, NAS or weather. Notebook 06's model cannot see it, because
it treats each flight independently. This notebook builds the aircraft's daily chain with a
window function over `(tail_number, flight_date)` and asks what that blindness costs.

**The propagation is not subtle.** Delay rate of a flight, by how late its inbound aircraft
arrived:

| Inbound arrived | Flights | Delay rate | vs 18.61% base |
|---|---|---|---|
| early / on time | 2,735,959 | 9.65% | −8.97 pp |
| 0–15 min late | 879,192 | 17.33% | −1.28 pp |
| 15–30 min late | 294,830 | 41.89% | +23.28 pp |
| 30–60 min late | 218,516 | 74.60% | +55.99 pp |
| 60–120 min late | 131,599 | **87.26%** | +68.65 pp |
| 2+ hours late | 67,649 | 80.59% | +61.98 pp |

Pearson correlation between the inbound's arrival delay and this flight's: **0.5078**.
Delay also compounds down the chain — leg 2 of the day runs 16.15% late, leg 7 runs 28.03%.

**Two models, same split, same hyperparameters, one difference — the feature set:**

| Model | ROC-AUC | F1 | Precision | Recall | Accuracy |
|---|---|---|---|---|---|
| Planning (no rotation) — weeks ahead | 0.7138 | 0.4165 | 0.3371 | 0.5450 | 0.7162 |
| **Day-of (with rotation) — hours ahead** | **0.8320** | **0.5967** | **0.6745** | 0.5350 | **0.8656** |
| Gain | **+0.1182** | **+0.1802** | +0.3374 | −0.0100 | +0.1494 |

The planning model at 0.7138 independently reproduces notebook 06's tuned GBT (0.7134)
through a different code path — a useful check that neither result is a fluke of one script.

**Precision doubled at unchanged recall.** The day-of model finds the same share of delays
while raising half as many false alarms. It also reaches **86.56% accuracy, beating the
81.39% majority-class baseline** that the planning model never clears.

`prev_arr_delay` alone carries **37.3%** of feature importance; the four rotation features
together carry **53.2%** — more than weather and every historical rate combined.

**This is not "the model improved."** The day-of model was given information the planning
problem does not have: the inbound aircraft's *actual* arrival delay, knowable hours before
departure, not weeks. A booking site cannot use it; an operations desk can. Quoting 0.8320
as an improvement on notebook 06 would be changing the question to make the answer look
better, so the two are reported separately and always together.

The notebook also records a **prediction it got wrong**: §5 originally argued the gain would
be bounded because turnaround slack absorbs delay. Slack does absorb delay — but only small
delay, and the argument reasoned about the average case in a distribution whose tail does
the damage.

## Documentation

| Document | Contents |
|---|---|
| [`docs/project_report.md`](docs/project_report.md) | Full report covering all six syllabus units, every figure measured on the running system |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | All 49 curated columns with real null percentages, generated from the live schema; marks post-departure fields excluded from the model |
| [`docs/nosql_comparison.md`](docs/nosql_comparison.md) | RDBMS vs NoSQL, CAP, the four NoSQL families, document modelling, indexing, sharding and replication |
| [`docs/engineering_decisions.md`](docs/engineering_decisions.md) | Rejected approaches, defects caught, limitations accepted, one retracted finding |
| [`docs/testing_and_performance.md`](docs/testing_and_performance.md) | Every measured figure in one place: ETL contracts, benchmarks, ablation, streaming |
| [`docs/deployment.md`](docs/deployment.md) | Deploying to Streamlit Community Cloud + MongoDB Atlas, and what the deployed version cannot do |

## Project status: complete

All 12 notebooks executed and verified, 7-page dashboard tested, documentation written.

| Optimisation | Gain |
|---|---|
| DataFrame vs RDD | 53× |
| MongoDB index (docs scanned) | 4,706× |
| Explicit schema vs inference | 8.2× |
| Caching a shuffled aggregate | 7.2× |
| CSV → Parquet storage | 3.9× |
