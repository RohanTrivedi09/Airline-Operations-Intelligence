# NoSQL: RDBMS Comparison, CAP, Types, Sharding & Replication

Unit 3 of the syllabus, applied to this project's serving layer.

---

## 1. RDBMS vs NoSQL — and why a document store here

| Aspect | RDBMS (e.g. PostgreSQL) | MongoDB (document) | This project |
|---|---|---|---|
| Schema | Fixed, declared up front, shared by every row | Per-document, no migration to add a field | The marts have genuinely different shapes — an airline document and a route document share no columns. One table per mart in SQL would be 10 tables and 10 migrations |
| Read pattern | Normalise, then join at query time | Denormalise, read one document | The dashboard reads one collection per page. Notebook 05 already did the joining, in Spark |
| Scaling | Vertical; sharding is bolted on | Horizontal sharding is native | Not needed at 1.8 MB, but the model supports it |
| Transactions | ACID across tables, mature | ACID within a document; multi-document since 4.0 | The serving layer is read-only after the batch push. No transactional requirement |
| Data format | Rows and columns | BSON documents | Maps directly to JSON for a web front-end with no ORM layer |
| Query language | SQL — expressive, declarative, standard | Query documents + aggregation pipeline | The complex analytics happen in SparkSQL, not here |

### The honest assessment

**A relational database would work perfectly well for this project.** At 6,076 documents
and 1.8 MB, no scaling argument favours MongoDB, and SQL would express the aggregations
more clearly than an aggregation pipeline.

The case for MongoDB here is narrower and specific: it is the **serving** layer, and the
thing being served is document-shaped. Each dashboard page needs one self-contained
document with no joins, which is exactly the document model's strength. The heavy
analytical work stays in Spark, where a relational engine's advantages would matter — and
SparkSQL already provides them.

Choosing MongoDB because "big data means NoSQL" would be the wrong reasoning. Choosing it
because the read path is a key-to-document lookup is defensible.

---

## 2. CAP theorem

CAP states that a distributed data store can guarantee at most **two** of:

- **Consistency** — every read returns the most recent write
- **Availability** — every request receives a response
- **Partition tolerance** — the system continues despite dropped messages between nodes

Since network partitions *will* happen in any real distributed system, partition tolerance
is not optional. The genuine choice is **CP or AP**.

### MongoDB is CP

In a replica set, all writes go to the **primary**, and reads default to the primary. A
client therefore never observes a stale value — consistency is preserved.

When the primary fails, the set holds an **election**. For the few seconds that takes,
**writes are rejected** — availability is what is sacrificed. Reads can continue from
secondaries if the application opts into `readPreference=secondaryPreferred`, which trades
consistency for availability on a per-query basis.

### Why CP is right for this workload

The dashboard reports operational metrics. Showing a figure that is silently out of date is
worse than showing a brief error and retrying, because a stale delay rate is
indistinguishable from a current one and will be acted on as if it were true.

### An honest caveat

**This deployment is a single MongoDB node in Docker.** There is no partition to tolerate
and no election to wait for, so CAP does not literally apply. The analysis above describes
how the system behaves *when deployed as a replica set* — which is how MongoDB Atlas runs
it, and how a production version of this project would run.

---

## 3. The four NoSQL families

| Type | Examples | Model | Strengths | Weaknesses |
|---|---|---|---|---|
| **Key-Value** | Redis, DynamoDB, Memcached | Opaque value under a key | Fastest possible lookup; trivial to shard | Cannot query by value; no partial reads |
| **Document** | MongoDB, CouchDB | JSON/BSON, nested, per-document schema | Query on any field; flexible schema; maps to APIs | Joins are awkward; denormalisation duplicates data |
| **Column-Family** | Cassandra, HBase | Rows with dynamic column families, sorted by key | Huge write throughput; excellent for time series | Query patterns must be known when modelling; no ad-hoc queries |
| **Graph** | Neo4j, JanusGraph | Nodes and edges with properties | Traversals and relationship queries are cheap | Poor fit for aggregate scans; harder to shard |

### Which would suit this project?

| Type | Verdict |
|---|---|
| **Document** ✅ | **Chosen.** Each dashboard page needs one self-contained document. Fields differ per mart. Query-on-any-field supports filters without new infrastructure |
| Key-Value | Workable — `airline:AA` → blob. But the map page filters on `cluster_id`, and a key-value store cannot query by value without maintaining a second index by hand |
| Column-Family | The right choice for the **raw flight records** if this ingested a live feed — write-heavy, time-ordered, 5.8M+ rows. Wrong for a 14-document airline collection |
| Graph | Genuinely interesting for *routes*: airports as nodes, routes as edges, enabling "shortest reliable path" or connection analysis. Not needed for the metrics this dashboard shows, but the most compelling extension of the four |

---

## 4. Data modelling in MongoDB

The governing principle is **model for the read pattern**, not for normal form.

Each collection answers one dashboard question:

| Collection | Answers | Documents |
|---|---|---|
| `overall_kpis` | Network summary | 1 |
| `airline_metrics` | Airline ranking and comparison | 14 |
| `airport_metrics` | Map, rankings, per-airport drill-down | 322 |
| `route_metrics` | Route lookup and reliability | 4,706 |
| `time_trends` | Monthly / hourly / weekday / seasonal | 47 |
| `delay_distribution`, `delay_causes` | Causes page | 11 |
| `airline_airport` | Airline performance at a given airport | 969 |
| `ml_classification_results`, `ml_clustering_results` | Model performance panels | 6 |

### Denormalisation, deliberately

`airport_metrics` stores `airport_name`, `city`, `state`, `lat`, `lon` inside every
document, duplicating what a relational design would keep in one `airports` table.

That duplication is the point: the map page issues **one query** and receives everything it
needs. The cost — stale copies if an airport is renamed — is irrelevant here, because the
entire collection is rebuilt from Parquet whenever notebook 08 runs.

### Multiple grains in one collection

`time_trends` holds monthly, hourly, day-of-week and seasonal rows, distinguished by a
`dimension` field. In SQL this would be four tables or a union view. In a document store
one collection with a discriminator is natural, and the index on `(dimension, period)`
keeps it fast.

---

## 5. Indexing — measured

Without an index, MongoDB performs a **collection scan** (`COLLSCAN`), examining every
document. An index turns that into a B-tree seek (`IXSCAN`).

Measured in notebook 08 with `explain()`, on a `route_metrics` lookup:

| | Documents examined | Returned | Stage |
|---|---|---|---|
| Before index | 4,706 | 1 | `COLLSCAN` |
| After compound index on `{origin, destination}` | **1** | 1 | `IXSCAN` |

At 4,706 documents the wall-clock saving is under a millisecond. The point is the **shape**
of the cost: a scan grows linearly with collection size, an index seek grows
logarithmically. This is the same argument as partition pruning in Parquet — avoid reading
what cannot match.

Indexes created, all derived from actual dashboard queries rather than added speculatively:

```javascript
airline_metrics : { airline_code: 1 }          // unique
airport_metrics : { airport_code: 1 }          // unique
airport_metrics : { cluster_id: 1 }            // map page filter
route_metrics   : { origin: 1, destination: 1 } // route lookup
route_metrics   : { delay_rate: 1 }            // ranking sort
time_trends     : { dimension: 1, period: 1 }  // trend queries
airline_airport : { airline_code: 1, airport_code: 1 }
```

Every index costs write time and storage (284 KB here, against 1.76 MB of data). Indexing
every field would be as wrong as indexing none.

---

## 6. Replication

A production MongoDB deployment is a **replica set**: one primary and two or more
secondaries.

- Writes go to the primary and are recorded in the **oplog**
- Secondaries tail the oplog and apply the same operations
- If the primary fails, the secondaries **elect** a new one (majority vote, hence the odd
  node count)

This provides fault tolerance (data survives node loss) and optional read scaling
(secondaries can serve reads under a relaxed read preference).

**Contrast with Spark's fault tolerance**, covered in notebook 10: MongoDB replicates
*data*; Spark records *lineage* and recomputes. Storage redundancy versus computational
redundancy — the same problem solved from opposite directions, appropriate to their
different jobs (durable storage versus transient computation).

**This project runs a single node.** No replication is configured, so a container failure
loses the serving layer — recoverable in seconds by re-running notebook 08, since the
Parquet marts are the source of truth. That the serving layer is disposable is itself a
design property worth noting.

---

## 7. Sharding

Sharding partitions a collection across multiple machines by a **shard key**.

**This project does not need it.** The entire serving layer is 1.8 MB; sharding it would
add a config server, query routers and network hops for no benefit.

Documented for completeness — how it *would* be applied if this ingested years of data:

| Collection | Sensible shard key | Reasoning |
|---|---|---|
| `route_metrics` | `{origin, destination}` | High cardinality (4,706), evenly distributed, and matches the dominant query so most lookups hit a single shard |
| `airport_metrics` | `airport_code` | 322 distinct values, every query filters on it |
| Raw flight records (hypothetical) | `{flight_date, airline_code}` | Compound key avoiding the monotonic-key hotspot that a date alone would create |
| `airline_metrics` | **would not shard** | 14 documents; overhead with zero benefit |

### Choosing a shard key badly

- **Low cardinality** — sharding on `cluster_id` (4 values) permits at most 4 chunks;
  most shards sit idle while a few are hot.
- **Monotonically increasing** — sharding on a timestamp alone sends every new write to
  the same shard, because all recent keys sort together. This is why the hypothetical raw
  key above is compound.
- **Not matching queries** — a key the queries do not filter on forces **scatter-gather**:
  every query hits every shard, which is worse than not sharding.

The lesson generalises beyond MongoDB: distribution keys must align with access patterns.
The same reasoning governs the choice to partition the curated Parquet by `month` in
notebook 02, since the dashboard and notebooks filter by time.
