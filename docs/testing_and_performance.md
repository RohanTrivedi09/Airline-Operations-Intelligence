# Testing & Performance Report

Deliverable from §23 of the project plan. Every figure here was measured on the running
system — Java 21, Python 3.12, PySpark 4.0, `local[6]`, 3–5 GB driver, 8 GB / 8-core machine.

---

## 1. Testing approach

There are no unit tests in the conventional sense. A data pipeline's correctness is not
mostly a function-level property — it is whether the right *rows* survive each stage — so
the checks are **assertions inside the pipeline** that fail the run rather than tests
alongside it.

| Layer | How it is verified |
|---|---|
| Environment | `scripts/smoke_test.py` — JVM starts, 5.8M rows read, shuffle completes |
| ETL | Row-count contract asserted at every stage; run aborts on unexplained loss |
| Joins | LEFT join + assertion that unmatched count is zero |
| Aggregates | Cross-checked against independently computed direct queries |
| Serving layer | MongoDB document counts asserted equal to source mart row counts |
| Dashboard | All 7 pages executed headlessly via `streamlit.testing.AppTest` |
| Notebooks | Every notebook executed end to end before commit — never only written |

### Defects these checks actually caught

Not hypothetical — each of these was found by an assertion failing, not by inspection:

| Defect | Caught by | Scale |
|---|---|---|
| October DOT airport codes | Join assertion | 486,165 rows (8.4%) |
| Destination-only airport code `10666` | Row-count contract | **1 row** of 5.8M |
| Spark workers on Python 3.14 vs driver 3.12 | First `createDataFrame` | Would break all MLlib |
| `subtract()` for test split | Printed positive rate | 94.6/5.4 split at 47.6% positive |
| Feature importances misaligned | Vector-width assertion | All 35 features mislabelled |
| `mode("overwrite")` onto a source path | Read failure on next run | Destroyed a mart |
| Map centred on (0,0) | Screenshot | US airports rendered over Africa |

The single-row catch is the argument for the whole approach: without the contract, that
run would have completed normally and one flight would have vanished from every
destination metric.

---

## 2. Storage and I/O

| Optimisation | Before | After | Gain |
|---|---|---|---|
| Explicit schema vs `inferSchema` | 3.9s | 0.5s | **8.2×** |
| CSV → Parquet (storage) | 565 MB | 144 MB | **3.9×** |
| 3-of-31-column scan | 0.6s | 0.2s | **2.7×** |
| Partition pruning (`month = 7`) | 12 directories | 1 | 12× fewer files opened |

Predicate pushdown and column pruning verified by reading the physical plan:
`PushedFilters: [EqualTo(status,completed)]`, `ReadSchema: 3 of 49 columns`.

**A subtlety worth recording:** a *cached* relation is substituted for a file scan, which
hides all file-level pruning from the plan. The first attempt at this measurement showed
zero optimisations for exactly that reason. Notebook 04 clears the cache before measuring.

---

## 3. Compute

| Measurement | Result |
|---|---|
| Lazy evaluation | 5 transformations 0.29s → `collect()` 1.22s |
| Narrow vs wide (shuffle) | 0.19s → 0.41s |
| Caching a shuffled aggregate | 1.60s → 0.22s (**7.2×**) |
| Partitioning | 24 partitions 0.99s vs 200 partitions 1.93s |
| RDD vs DataFrame vs SparkSQL | 21.91s / 0.41s / 0.28s (**53× / 78×**) |
| Iterative workload, 5 passes | 29.52s uncached vs 12.39s cached (2.4×) |
| Fault tolerance | Cache destroyed; result recomputed from lineage, asserted identical |

### Scaling: sample vs full dataset

| Sample | Rows | Time | Throughput |
|---|---|---|---|
| 1% | 58,227 | 1.23s | 0.05M rows/s |
| 10% | 581,607 | 0.67s | 0.86M rows/s |
| 50% | 2,908,568 | 2.76s | 1.05M rows/s |
| 100% | 5,819,078 | 3.54s | 1.64M rows/s |

**Time grows sub-linearly with data: 100× the rows costs ~5.6× the time.** Fixed per-job
overhead — query planning, task scheduling, JVM warm-up — dominates the small samples and
amortises away as data grows, so throughput *rises* with scale. No quadratic behaviour and
no spilling appears at this size on this machine.

### A benchmarking caveat, learned the hard way

An earlier run of this measurement showed the 100% case taking **6.5×** the 50% case, with
throughput collapsing from 1.05M to 0.33M rows/s. That looked exactly like an 8 GB memory
wall, and it was written up as one.

It was not. An unrelated model-training job was running concurrently and competing for CPU.
Re-run on an idle machine, the same job scales cleanly.

The lesson is worth more than the number: **a timing on a shared machine measures the
machine, not the code.** A plausible mechanism (memory spill) was available to explain the
artefact, which is precisely what made the wrong conclusion easy to reach.

---

## 4. Serving layer

| Measurement | Result |
|---|---|
| Marts on disk | 276 KB (vs 201 MB curated, 565 MB raw) |
| MongoDB | 18 collections, 18,186 documents, 1.76 MB data + 284 KB indexes |
| Index effect | `COLLSCAN` 4,706 docs → `IXSCAN` **1 doc** |
| Dashboard query latency | 0.3–1.3 ms per page |

At 4,706 documents the wall-clock index saving is sub-millisecond. The point is the shape
of the cost: a scan grows linearly with collection size, an index seek logarithmically.

---

## 5. Machine learning

Ablation, all on the same held-out split of 1,143,441 flights:

| Step | ROC-AUC | F1 | Δ AUC |
|---|---|---|---|
| Logistic Regression | 0.6503 | 0.3678 | — |
| Random Forest | 0.6626 | 0.3765 | +0.0123 |
| + tuned threshold | 0.6626 | 0.3765 | **+0.0000** |
| + weather | 0.6771 | 0.3849 | +0.0145 |
| + interactions | 0.6811 | 0.3874 | +0.0040 |
| Gradient-Boosted Trees | 0.6976 | 0.4008 | +0.0165 |
| **GBT, tuned** | **0.7134** | **0.4165** | +0.0158 |
| *Temporal split* | *0.6580* | *0.3389* | *honesty check* |

**Null result reported, not dropped:** threshold tuning gained exactly nothing on the
weighted Random Forest, because class weighting had already put the F1 optimum at 0.50. It
does earn its place later — GBT's optimum is 0.55.

**Weather underdelivered relative to its crosstabs.** Freezing precipitation shows a 54.65%
delay rate against a 19.05% base, but is 0.18% of flights; a large effect on a small slice
moves AUC little. Weather still carries 28.5% of total feature importance.

**The temporal split is the honest forecasting number.** ROC-AUC drops 0.7134 → 0.6580 when
training on Jan–Sep and testing Oct–Dec, partly because the delay rate itself shifts from
19.45% to 16.07% across the boundary.

Training cost: LR 25s, RF 205s, GBT 386s, hyperparameter search 801s over 4 configurations.

---

## 6. Streaming

| Measurement | Result |
|---|---|
| Events processed | 16,989 across 8 micro-batches |
| Rolling delay rate | 28.98% — **identical to the batch figure** |
| Correctness | Streaming result asserted equal to batch over the same rows |
| Recovery | Checkpoint (`offsets`, `commits`, `state`) gives exactly-once |

---

## 7. Known limitations

1. **Single machine.** `local[6]` demonstrates the programming model but not distributed
   execution. Scaling here measures amortisation of fixed overhead, not the horizontal
   scaling a cluster provides.
2. **`reduceByKey` vs `groupByKey` showed only ~1.2×** across four key cardinalities.
   There is no network on one machine for a combiner to save. The syllabus principle holds;
   this environment cannot demonstrate it.
3. **A file source is not Kafka.** Same programming model; no partitioned consumption,
   offset replay or back-pressure.
4. **Single-node MongoDB.** No replica set, so the CAP analysis describes production
   behaviour rather than what runs here.
5. **Model ceiling.** Pre-departure features cannot see the inbound aircraft running late —
   39.8% of delay minutes. Notebook 12 addresses this, at the cost of changing the
   prediction horizon from planning to day-of.
