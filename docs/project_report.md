# Airline Operations Intelligence Platform — Project Report

**Course:** Big Data Analytics · **Type:** End-to-end big data analytics and decision-support platform

Every figure in this report was measured on the actual system. Nothing is estimated.

---

## 1. What was built

A complete pipeline from raw CSV to an interactive dashboard:

```
Dataset/flights.csv   565 MB   5,819,079 rows
   ↓  notebook 01 — load, audit, freeze schema
data/raw/*.parquet    137 MB   partitioned by month
   ↓  notebook 02 — 11 cleaning rules, row-count contract
data/curated/*.parquet 201 MB  5,819,078 rows × 49 columns
   ↓  notebooks 05–07 — aggregations, classification, clustering
data/marts/*.parquet  276 KB   6,076 documents
   ↓  notebook 08 — push + index
MongoDB               1.76 MB  10 collections
   ↓
Streamlit dashboard   6 pages, all queries < 2 ms
```

**Environment:** Java 21.0.2, Python 3.12.1, PySpark 4.0.0, `local[6]`, 3 GB driver, on an
8 GB / 8-core machine. Everything runs locally; no cloud services required.

---

## 2. Unit 1 — Big Data characteristics

### The 5 V's, with measured evidence

| V | Evidence from this project |
|---|---|
| **Volume** | 5,819,079 flight records × 31 raw columns, 565 MB CSV. Too large for spreadsheet tools; comfortable for Spark |
| **Variety** | Structured CSV (flights, airlines, airports), columnar Parquet, semi-structured BSON documents in MongoDB, JSON model artefacts |
| **Velocity** | Notebook 09 replays 16,989 flights through Spark Structured Streaming in 6 micro-batches, with state accumulating across batches |
| **Veracity** | The core finding of notebook 01: **486,165 flights (8.4%) carry DOT numeric airport codes instead of IATA**, and a naive inner join deletes them silently. Plus 105,071 structural nulls and 1 duplicate business key |
| **Value** | Delay causes quantified (late aircraft 39.8% of delay minutes), airports grouped into 4 operational profiles, delay risk predicted at ROC-AUC 0.663 |

### Veracity in detail — the defect that mattered most

For **October 2015 only**, `ORIGIN_AIRPORT` and `DESTINATION_AIRPORT` store 5-digit DOT
codes rather than 3-letter IATA codes. `airports.csv` is IATA-keyed, so an inner join
discards those 486,165 rows **without raising an error**. The pipeline would succeed and
every airport, route and monthly metric would be quietly wrong.

This is the characteristic big-data failure: not a crash, but confidently incorrect output
at a scale nobody can eyeball.

**Recovered without an external lookup table.** `DISTANCE` is deterministic per airport
pair, so the *set* of distances an airport flies is a fingerprint. Fingerprints alone tie
for small airports (23 DOT codes match ATL perfectly), so flight volume was added as a
second signal, scores resolved to a strict one-to-one assignment, and the result validated
against a signal it was not fitted on — each October route's distance must match that IATA
pair in the other 11 months.

**Result: 307/307 codes resolved, 99.910% distance agreement (±1 mile).**

### Challenges encountered

| Challenge | How it appeared | Resolution |
|---|---|---|
| Missing values | 81.72% null in delay-cause columns | Proved structural: populated for exactly the 1,063,439 flights arriving 15+ late |
| Inconsistent codes | October's DOT codes | Data-driven recovery, validated |
| Duplicates | 1 business-key collision in 5.8M rows | Deduplicated on a 7-column key |
| Join complexity | 3 sources, 2 join keys | LEFT joins with asserted zero unmatched |
| Class imbalance | 18.61% positive | Class weights; F1 and ROC-AUC reported, not accuracy |
| Memory limits | 8 GB, driver OOM during training | `MEMORY_AND_DISK` + staged unpersists |

---

## 3. Unit 2 — Frameworks and MapReduce

### Distributed computing

PySpark distributes ETL, aggregation and ML across 6 task slots. In `local[6]` the driver
and executors share one JVM; the same code runs unchanged on a cluster, with only the
master URL differing.

### HDFS concepts (documented, not deployed)

HDFS splits files into 128 MB blocks replicated 3× across DataNodes, with a NameNode
holding the metadata. This project uses the local filesystem, but two HDFS-ecosystem
properties are used directly:

- **Parquet** — the Hadoop columnar format, with embedded schema and per-column compression
- **Directory partitioning** — `month=7/` layout, the same scheme Hive and HDFS-based tools use

### MapReduce, demonstrated (notebook 03)

`map` → shuffle → `reduceByKey` implemented on real data, including the awkward case:
computing an average requires carrying `(sum, count)` pairs through the reduce and dividing
at the end, because averages are not associative.

### Limitations of MapReduce, measured

| Limitation | Evidence |
|---|---|
| Disk I/O between jobs | 5 iterative passes: **29.52s** recomputing vs **12.39s** cached (2.4×) |
| Verbosity | Average delay: 4 chained RDD operations with manual `(sum, count)` vs one `groupBy().agg()` |
| No optimisation | RDD 21.91s vs DataFrame 0.41s for an identical result (**53×**) |
| Rigid model | Only map-then-reduce, versus an arbitrary DAG |

### Batch vs real-time

| Aspect | Batch (01–08) | Streaming (09) |
|---|---|---|
| Schema | Inferred once | **Must** be declared — no data may exist at start |
| Trigger | Manual | Automatic on new files |
| State | None between runs | Checkpointed, survives restart |
| Latency | Minutes over 5.8M rows | Sub-second per micro-batch |

Notebook 09 asserts the streaming result is **identical to the batch result** over the same
16,989 rows — the same DataFrame code, two execution modes.

---

## 4. Unit 3 — NoSQL

Covered in full in [`nosql_comparison.md`](nosql_comparison.md): RDBMS vs NoSQL with an
honest assessment that a relational database would also work at this size, CAP applied to
MongoDB (CP, with the caveat that this single node has no partition to tolerate), the four
NoSQL families, document modelling for read patterns, and sharding/replication.

**Indexing, measured** (notebook 08): a route lookup goes from `COLLSCAN` examining all
4,706 documents to `IXSCAN` examining **1**.

---

## 5. Unit 4 — Apache Spark

### The three APIs, benchmarked on identical output (notebook 03)

| API | Time | vs RDD |
|---|---|---|
| RDD `map`/`reduceByKey` | 21.91s | 1.0× |
| DataFrame `groupBy().agg()` | 0.41s | **53×** |
| SparkSQL | 0.28s | **78×** |

DataFrame and SparkSQL compile to the *same* Catalyst plan — verified by comparing
optimised plans after normalising expression ids.

### Core concepts, each measured (notebook 10)

| Concept | Measurement |
|---|---|
| Lazy evaluation | 5 transformations 0.29s → `collect()` 1.22s |
| Narrow vs wide | 0.19s → 0.41s once a shuffle is introduced |
| Partitioning | 24 partitions 0.99s vs 200 partitions 1.93s |
| Caching a shuffled aggregate | 1.60s → 0.22s (**7.2×**) |
| Fault tolerance | Cache destroyed; result **recomputed from lineage** and asserted identical |
| Explicit schema | 8.2× faster load than `inferSchema` |
| Parquet vs CSV | 565 MB → 144 MB; 2.7× faster 3-of-31-column scan |

### Catalyst, read off the physical plan (notebook 04)

- `PartitionFilters: [(month = 7)]` — prunes 11 of 12 directories at file level
- `PushedFilters: [EqualTo(status,completed)]` — evaluated inside the Parquet reader
- `ReadSchema:` 3 of 49 columns — the other 46 never read

### Fault tolerance: lineage vs replication

Hadoop replicates data (3 copies). Spark records **how to recompute** each partition.
Notebook 10 destroys every cached partition and rebuilds the result, asserting equality
with the pre-loss answer — computational redundancy rather than storage redundancy.

---

## 6. Unit 5 — Analytics and machine learning

### Preprocessing

11 rules derived from evidence in notebook 01, implemented in notebook 02 with a
**row-count contract** asserted at every stage. Result: **100.000% retention**
(5,819,078 of 5,819,079; the single lost row is the duplicate key).

### Classification — delay prediction (notebook 06)

Target: arrival delay ≥ 15 minutes. Test set 1,143,441 rows.

| Metric | Logistic Regression | Random Forest | Baseline |
|---|---|---|---|
| Accuracy | 0.6005 | 0.6098 | **0.8139** |
| Precision | 0.2608 | 0.2678 | — |
| Recall | 0.6248 | **0.6324** | — |
| F1 | 0.3680 | **0.3763** | — |
| ROC-AUC | 0.6501 | **0.6626** | — |

**Accuracy below baseline is the intended trade, not a failure.** Class weighting (4.373×)
sacrifices accuracy to catch delays: the forest identifies **134,596 of 212,844 delayed
flights (63%)**, where an unweighted model scoring 81.4% would catch almost none.

Two methodological safeguards:

1. **Leakage enforced in code.** A `BANNED` set (`dep_delay`, taxi times, `air_time`,
   actual times, cause columns) is asserted against the feature set before training.
2. **Historical rate features computed from the training split only**, with Bayesian
   smoothing toward the global mean. Computing them over the full dataset would leak
   test-set outcomes into training features — a subtle and common error.

Top features: `sched_dep_hour` (0.232), `route_delay_rate` (0.174),
`time_of_day=morning` (0.108).

**The ceiling is inherent.** Pre-departure features cannot observe day-of weather, the
inbound aircraft running late (39.8% of delay minutes), or ATC decisions. Large irreducible
error is the correct result.

### Clustering — airport profiles (notebook 07)

K-Means over 6 operational features, on the 80 airports meeting the 10,000-flight
threshold. k = 4 (silhouette 0.351; WCSS 226.8).

| Profile | Airports | Avg flights | Delay rate | Examples |
|---|---|---|---|---|
| High-traffic hub, elevated delays | 16 | 170,858 | 20.6% | ATL, ORD, DFW, DEN, LAX |
| High-traffic hub, well-managed | 33 | 47,141 | 17.1% | MSP, SEA, DTW, CLT |
| Smaller airport, elevated delays | 21 | 26,998 | 18.0% | MDW, MIA, DAL, HOU |
| Smaller airport, reliable | 10 | 33,525 | 12.5% | SLC, PDX, HNL, SNA |

`StandardScaler` is essential: `total_flights` spans 50–300,000 while rates are 0–100, so
unscaled K-Means would simply sort airports by size.

Silhouette alone prefers k=2 (0.446), but two clusters cannot distinguish airport types
usefully. Both criteria are reported so the choice is auditable rather than asserted.

### Analytical findings

Overall: **81.39% on-time**, 18.61% delayed, 1.54% cancelled, 0.26% diverted.

| Delay cause | Share of delay minutes | Avg min per late flight |
|---|---|---|
| Late aircraft | 39.84% | 23.47 |
| Carrier | 32.20% | 18.97 |
| NAS | 22.88% | 13.48 |
| Weather | 4.95% | 2.92 |
| Security | 0.13% | 0.08 |

Best airline: Hawaiian (11.33% delay rate). Worst: Spirit (29.71%). Delay risk compounds
through the operating day and resets overnight — consistent with late aircraft being the
dominant cause.

---

## 7. Unit 6 — Applications, ethics, privacy and bias

### Application domain
Aviation and transportation analytics — a documented real-world big-data domain, generating
continuous high-volume operational data.

### Privacy and security
- **No passenger PII.** The dataset contains operational records only: no names, bookings
  or personal data. `TAIL_NUMBER` identifies aircraft, not people.
- **Credentials never hardcoded.** MongoDB URI in `.env`, git-ignored, with `.env.example`
  committed. Verified: `.gitignore` excludes `.env`, `Dataset/*.csv`, `data/`.
- **Local deployment** — no data leaves the machine.

### Ethical concerns
- **Fair airline comparison.** Sample sizes accompany every rate throughout the dashboard.
- **Historical limitation.** 2015 data does not describe airlines today. The platform is an
  academic analytics tool and states so; it is not for booking decisions.
- **Self-reported delay causes.** Carriers report their own carrier/weather/NAS attribution,
  so a systematic incentive to under-report carrier fault cannot be ruled out. Documented.
- **Licensing.** US DOT/BTS data is public domain; OurAirports is open data.

### Bias, identified and mitigated

| Bias | Evidence | Mitigation |
|---|---|---|
| **Small-sample** | Unfiltered, the "worst" airport is GST at 44.74% on **76 flights**; with a 10,000-flight threshold it is LGA at 23.39% on **103,281** | `HAVING`/`meets_min_sample` thresholds before every ranking; sample sizes always shown |
| **Class imbalance** | 81.4% accuracy achievable by always predicting "on time" | Class weights; F1, recall, ROC-AUC and confusion matrix reported alongside accuracy |
| **Clustering small airports** | 200-flight airports would receive confident but noise-driven labels | Only the 80 eligible airports are clustered; the rest keep all metrics with `cluster_id = null` |
| **Geographic** | US domestic only | Stated; results do not generalise internationally |
| **Temporal** | Single year | Stated; seasonal patterns may not hold across years |
| **Coverage** | 3 airports lack coordinates | Retained in all metrics, excluded from the map only |

---

## 8. Evaluation

### Data engineering
Pipeline runs raw CSV → curated Parquet → MongoDB, reproducibly. Row-count contract
asserted at every ETL stage; **100.000% retention**. KPIs cross-checked against independent
direct queries (all match to 0.01); airline, airport and route totals each reconcile to
5,819,078.

### Performance

| Optimisation | Before | After | Gain |
|---|---|---|---|
| Explicit schema vs inference | 3.9s | 0.5s | 8.2× |
| CSV → Parquet (storage) | 565 MB | 144 MB | 3.9× |
| Partial-column scan | 0.6s | 0.2s | 2.7× |
| Caching a shuffled aggregate | 1.60s | 0.22s | 7.2× |
| DataFrame vs RDD | 21.91s | 0.41s | 53× |
| MongoDB index | 4,706 docs scanned | 1 | 4,706× |

### Dashboard
Six pages, all verified headlessly with `streamlit.testing.AppTest` — zero exceptions. The
prediction path was exercised end to end. With MongoDB stopped, all pages still render from
the Parquet fallback.

---

## 9. Limitations and honest caveats

1. **Random rather than temporal train/test split.** The plan specifies stratified
   splitting, which is implemented, but a time-based split (train Jan–Sep, test Oct–Dec)
   would be the more honest test of a forecasting claim.
2. **Local mode cannot measure distributed cost.** `reduceByKey` vs `groupByKey` showed
   only ~1.2× here, because a single machine has no network for a combiner to save. The
   syllabus principle stands; this environment cannot demonstrate it.
3. **A file source is not Kafka.** The streaming programming model is identical, but
   partitioned consumption, offset replay and back-pressure are not exercised.
4. **Single-node MongoDB.** No replica set, so the CAP analysis describes how it would
   behave in production, not what is running.
5. **7 airports (617 flights, 0.011%) validate below 95%** in the DOT-code recovery —
   tiny and seasonal airports. Documented rather than hidden.
6. **Model ceiling.** ROC-AUC 0.663 reflects what is knowable before departure. Weather
   enrichment is the main avenue for improvement.

---

## 10. Deliverables

| Deliverable | Location |
|---|---|
| 10 Colab-style notebooks, all executed | `notebooks/` |
| Curated Parquet + marts | `data/` (git-ignored, regenerable) |
| MongoDB serving layer | `docker compose up -d`, notebook 08 |
| Streamlit dashboard, 6 pages | `app/` |
| Project report | this file |
| Data dictionary | `docs/data_dictionary.md` |
| NoSQL analysis | `docs/nosql_comparison.md` |
| Engineering decisions and defects | `docs/engineering_decisions.md` |
| Environment smoke test | `scripts/smoke_test.py` |

### Reproducing from scratch

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "pyspark[sql]==4.0.0" pandas pyarrow \
    ipykernel pymongo python-dotenv streamlit plotly
.venv/bin/python scripts/smoke_test.py        # expect PASS
# run notebooks 01 → 10 in order
docker compose up -d
.venv/bin/streamlit run app/Home.py
```
