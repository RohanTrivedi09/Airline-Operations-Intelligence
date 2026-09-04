# Airline Operations Intelligence Platform

## Project Proposal (Updated)

**Course:** Big Data Analytics
**Developer:** Solo project
**Proposed duration:** 8 weeks
**Project type:** End-to-end big data analytics and decision-support platform

---

## Development Environment Split

This project uses a split development environment. Any AI coding assistant should be aware of this separation when generating code or instructions.

### Google Colab (browser-based notebooks)

All data-heavy processing runs in Colab notebooks:

- Dataset loading and exploration
- PySpark ETL — cleaning, validation, transformation
- RDD demonstrations and DataFrame operations
- SparkSQL queries
- Spark aggregations — airline, airport, route, time-based metrics
- Feature engineering and ML model training (Spark MLlib — classification and clustering)
- MapReduce concept demonstration
- Streaming analytics demonstration (Spark Structured Streaming with file source)
- Exporting results to Parquet/CSV
- Pushing precomputed summaries to MongoDB Atlas via `pymongo`

### Local machine (VS Code)

The dashboard and serving layer run locally:

- Streamlit web app
- MongoDB Atlas connection via `pymongo` (read-only from dashboard side)
- Plotly visualizations
- Final integration, testing, and demo

### MongoDB Atlas (cloud — free tier)

- Acts as the **serving layer** — precomputed aggregation documents
- Demonstrates document-based NoSQL storage, data modeling, sharding awareness, and replication concepts
- Accessible from both Colab (write) and local Streamlit (read)
- Free tier: 512 MB storage, sufficient for this project

### Data flow

```text
[Colab]                                          [Local]
Kaggle CSV                                       Streamlit app
   │                                                │
   ▼                                                │
PySpark ETL (clean, validate, transform)            │
   │                                                │
   ▼                                                │
Spark aggregations + ML training                    │
   │                                                │
   ▼                                                ▼
pymongo push ──────► MongoDB Atlas ◄────── pymongo read
                   (precomputed docs)
```

---

## 1. Project Overview

The **Airline Operations Intelligence Platform** is an end-to-end system for collecting, processing, analyzing, and visualizing airline flight operations data. The platform will help users understand flight delays, cancellations, airport congestion, airline performance, route reliability, and operational patterns.

The final product will be more than a static dashboard. It will combine:

- A data ingestion and ETL pipeline
- Distributed processing using Apache Spark
- Structured analytical datasets
- NoSQL storage for flexible access and dashboard queries
- Interactive dashboards for operational intelligence
- Machine learning for delay prediction (classification) and airport grouping (clustering)
- A streaming analytics demonstration using Spark Structured Streaming

The dashboard will act as the user-facing layer, while the data engineering, analytics, and machine learning components demonstrate the Big Data concepts covered in the course.

### Expected final outcome

A working prototype in which a user can explore airline and airport performance, investigate delay causes, compare routes, identify high-risk operating conditions, and view data-driven insights through an interactive web interface.

---

## 2. Why This Project Was Chosen

Airline operations are a strong Big Data use case because the industry generates large, varied, and continuously changing datasets. Flight records can be combined with airport, weather, carrier, aircraft, and schedule information to answer realistic operational questions.

This project was selected because it provides a practical balance between academic depth, implementation feasibility, and presentation value.

### Main reasons

1. **Relevant and understandable domain**
   Flight delays and cancellations are easy to explain to evaluators while still offering meaningful analytical depth.

2. **Publicly available datasets**
   Government and research datasets provide millions of historical flight records, making the project suitable for distributed processing.

3. **Strong fit for Big Data tools**
   Spark can be used for ingestion, transformation, aggregation, feature engineering, and machine learning.

4. **Clear end-to-end workflow**
   The project naturally demonstrates the flow from raw data to cleaned data, analytics, predictions, and decisions.

5. **Manageable within an academic timeline**
   A well-scoped historical analytics platform can be completed within eight weeks, with advanced extensions treated as optional.

6. **Good demonstration potential**
   Interactive maps, airline rankings, route comparisons, and delay predictions make the final presentation engaging.

---

## 3. Big Data Characteristics in This Project

This section explicitly maps the project's data to the foundational Big Data concepts from the syllabus.

### The 5 V's

| V | How demonstrated |
|---|---|
| **Volume** | ~5.8 million flight records in the Kaggle 2015 dataset. BTS data can scale to tens of millions across multiple years. |
| **Variety** | Structured CSVs (flights, airlines, airports), semi-structured JSON (API responses, MongoDB documents), and potential unstructured data (weather text reports, METAR strings). |
| **Velocity** | Historical batch data for core analytics. Streaming demonstration simulates velocity by replaying flight events through Spark Structured Streaming. |
| **Veracity** | Real-world data quality issues — missing delay fields, cancelled flights with no delay data, inconsistent airport codes, duplicate records. Cleaning pipeline addresses veracity directly. |
| **Value** | Actionable insights — delay predictions, route reliability rankings, airline performance comparisons — demonstrate extracting value from raw operational data. |

### Types of data handled

| Type | Example in this project |
|---|---|
| **Structured** | Flight CSV with fixed schema (date, airline, origin, destination, delay minutes) |
| **Semi-structured** | MongoDB JSON documents with flexible nested fields, OurAirports data with optional columns |
| **Unstructured** | Weather text observations (METAR/TAF strings), if weather enrichment is added as extension |

### Key challenges demonstrated

- Processing millions of records efficiently (distributed computing via Spark)
- Handling missing and inconsistent data at scale (ETL pipeline)
- Joining heterogeneous data sources (flights + airports + optionally weather)
- Choosing appropriate storage for different access patterns (Parquet for analytics, MongoDB for serving)
- Avoiding misleading conclusions from large but imbalanced data (class imbalance in ML)

---

## 4. Alignment with the Big Data Analytics Syllabus

| Syllabus Unit | Syllabus Topic | How the project demonstrates it |
|---|---|---|
| **Unit 1: Introduction** | 5 V's of Big Data | Mapped explicitly in Section 3 — Volume (5.8M rows), Variety (CSV + JSON + optional text), Velocity (streaming demo), Veracity (data quality issues), Value (actionable insights) |
| | Types of data | Structured (flight CSVs), semi-structured (MongoDB JSON docs), unstructured (weather text, if extended) |
| | Challenges in Big Data | Missing values, duplicates, schema inconsistencies, join complexity, class imbalance |
| | Applications of Big Data | Aviation / transportation industry analytics — a real-world Big Data application domain |
| **Unit 2: Frameworks** | Distributed and Parallel Computing | PySpark distributes ETL, aggregations, and ML across available cores |
| | Hadoop Ecosystem Overview | PySpark runs on Hadoop-compatible engine; Parquet is a Hadoop-ecosystem columnar format; HDFS concepts discussed in documentation |
| | HDFS Architecture | Documented in project report — block storage, replication, namenode/datanode concepts explained even if local mode used |
| | MapReduce Programming Model | Dedicated notebook demonstrates a word-count and a flight-delay-count using raw RDD `map()` and `reduceByKey()` before switching to DataFrames |
| | Limitations of MapReduce | Documented comparison — disk I/O overhead, no iterative processing support, verbosity vs Spark's in-memory DAG execution |
| | Real-time vs Batch Processing | Batch pipeline is the core; streaming notebook demonstrates real-time concept using Spark Structured Streaming with file source; comparison documented |
| **Unit 3: NoSQL** | RDBMS vs NoSQL | Project report includes comparison table — why MongoDB (schema flexibility, horizontal scaling, JSON-native) suits this project's serving layer vs a relational DB |
| | CAP Theorem | Documented analysis — MongoDB Atlas defaults to CP (consistency + partition tolerance); tradeoffs explained in project report |
| | Types of NoSQL Databases | MongoDB demonstrates Document DB. Project report discusses Key-Value (Redis), Column-Family (Cassandra/HBase), and Graph (Neo4j) with rationale for choosing Document DB for this use case |
| | Data Modeling in NoSQL | MongoDB collection schemas designed for dashboard query patterns — denormalized, pre-aggregated documents |
| | Sharding and Replication | MongoDB Atlas replication explained; sharding concepts documented; `airline_code` or `airport_code` discussed as potential shard keys |
| **Unit 4: Apache Spark** | Spark vs Hadoop MapReduce | Direct comparison demonstrated — same delay-count task done via RDD MapReduce-style and via DataFrame API; execution time compared |
| | Spark Ecosystem Overview | PySpark (Spark Core), Spark SQL, Spark MLlib, Spark Structured Streaming — all used in the project |
| | Spark Architecture | Documented — driver, executors, cluster manager, job/stage/task breakdown |
| | RDD Concepts | Dedicated notebook cells demonstrate RDD creation, transformations (`map`, `filter`, `reduceByKey`), and actions (`collect`, `count`, `take`) |
| | DataFrames and Datasets | Primary data structure for ETL and analytics — schema enforcement, column operations, joins |
| | Lazy Evaluation and DAG | Documented with examples — transformations are lazy, actions trigger execution. DAG visualization via Spark UI screenshots |
| | SparkSQL | SQL queries on flight data — `CREATE TEMP VIEW`, then `SELECT airline, AVG(delay) ... GROUP BY` to produce same results as DataFrame API |
| | Fault Tolerance | Documented — RDD lineage graphs, DAG recomputation on failure, Spark's approach vs HDFS replication |
| **Unit 5: Analytics** | Data Preprocessing | PySpark ETL — missing value handling, type casting, deduplication, outlier detection, normalization of categorical codes |
| | Scalable ML Algorithms | Spark MLlib — designed for distributed training on large datasets |
| | Classification | Binary delay prediction (>15 min) using Logistic Regression and Random Forest via MLlib |
| | Clustering | K-Means clustering on airports using features like avg delay, flight volume, cancellation rate — groups airports into operational profiles (e.g., high-traffic-high-delay, low-traffic-reliable) |
| | Apache Spark MLlib | Feature engineering via VectorAssembler, StringIndexer; model training, evaluation, and pipeline API |
| | Streaming Analytics | Spark Structured Streaming notebook — simulates incoming flight events from CSV, computes rolling delay counts, demonstrates micro-batch processing |
| | Challenges of ML in Big Data | Class imbalance (~80% on-time), feature leakage prevention, distributed training overhead, interpretability of results |
| **Unit 6: Applications & Ethics** | Big Data Applications | Aviation/transportation analytics — a documented real-world application domain |
| | Security and Privacy | Discussion of PII in flight data (passenger data not used), MongoDB Atlas access control, connection string security, API key management |
| | Ethical and Legal Concerns | Data usage terms (BTS/DOT public data license), responsible reporting of airline/airport performance, avoiding unfair rankings |
| | Bias and Fairness | Analysis of potential bias — small-sample airlines getting extreme rankings, geographic bias in airport coverage, class imbalance creating biased predictions. Mitigations documented |

---

## 5. Project Objectives

### Primary objectives

- Build a complete pipeline for airline operations data.
- Process a large historical dataset using Apache Spark.
- Demonstrate RDD operations, DataFrame API, and SparkSQL.
- Store both raw and curated data in appropriate formats.
- Use MongoDB as a NoSQL serving layer with documented data modeling decisions.
- Produce reliable operational KPIs and analytical summaries.
- Develop an interactive dashboard for exploration and decision support.
- Demonstrate both classification and clustering ML use cases.
- Include a streaming analytics demonstration.
- Document Big Data concepts (5 V's, CAP theorem, MapReduce vs Spark, RDBMS vs NoSQL) with project-specific examples.
- Evaluate the system using technical and analytical metrics.

### Secondary objectives

- Combine flight data with airport or weather information.
- Compare batch analytics with streaming or micro-batch processing.
- Use partitioning and columnar formats to improve query performance.
- Present interpretable findings rather than only displaying charts.
- Discuss ethical, privacy, and bias considerations in the project report.

### Questions the platform should answer

- Which airlines have the highest delay rates?
- Which airports experience the most delays and congestion?
- Which routes are the least reliable?
- At what times and on which days do delays increase?
- What are the most common operational causes of delay?
- How does weather or airport congestion relate to delays?
- Can a flight's delay risk be predicted before departure?
- Can airports be grouped into operational profiles based on their performance characteristics?

---

## 6. Proposed Architecture

```text
         ┌──────────────────────────────────────┐
         │     Interactive Dashboard (Streamlit)  │
         │ KPIs • Charts • Maps • Filters • ML  │
         └───────────────────▲──────────────────┘
                             │
         ┌───────────────────┴──────────────────┐
         │     MongoDB Atlas (Serving Layer)      │
         │  Precomputed docs • ML results • KPIs │
         └───────────────────▲──────────────────┘
                             │
       ┌─────────────────────┴─────────────────────────┐
       │        Apache Spark Processing (Colab)          │
       │ RDD ops • DataFrames • SparkSQL • MLlib         │
       │ ETL • Aggregations • Classification • Clustering│
       └─────────────────────▲─────────────────────────┘
                             │
       ┌─────────────────────┴─────────────────────────┐
       │              Data Ingestion (Colab)              │
       │ Batch CSV files • Parquet conversion              │
       │ Optional: Simulated streaming via file source     │
       └─────────────────────▲─────────────────────────┘
                             │
       ┌─────────────────────┴─────────────────────────┐
       │           Raw Data Storage (Colab / Drive)       │
       │ CSV files • Cleaned Parquet on Google Drive       │
       └───────────────────────────────────────────────┘
```

### Processing stages

1. **Ingestion:** Collect flight records and supporting datasets.
2. **Raw storage:** Preserve the original data for reproducibility.
3. **Cleaning:** Handle missing values, invalid records, duplicate rows, and inconsistent codes.
4. **Transformation:** Standardize dates, times, categorical values, and airport or airline identifiers.
5. **Enrichment:** Join flight records with airport and carrier data.
6. **Analytics:** Generate aggregations and operational metrics using Spark.
7. **Feature engineering:** Prepare inputs for predictive and clustering models.
8. **Serving:** Push dashboard-ready results to MongoDB Atlas.
9. **Visualization:** Present insights through the Streamlit dashboard.

---

## 7. Proposed Technology Stack

| Layer | Technology | Where it runs |
|---|---|---|
| Language | Python | Both |
| Distributed processing | Apache Spark with PySpark | Colab |
| Raw storage | CSV → Parquet (Google Drive for persistence) | Colab |
| NoSQL | MongoDB Atlas (free tier) | Cloud |
| Dashboard | Streamlit | Local |
| Visualization | Plotly, Streamlit native charts | Local |
| ML — Classification | Spark MLlib (LogisticRegression, RandomForest) | Colab |
| ML — Clustering | Spark MLlib (KMeans) | Colab |
| Streaming demo | Spark Structured Streaming (file source) | Colab |
| Connection | pymongo | Both |
| Version control | Git + GitHub | Local |

---

## 8. Datasets

### Core flight dataset

**Kaggle 2015 Flight Delays and Cancellations**
- Source: https://www.kaggle.com/datasets/usdot/flight-delays
- Original source: U.S. DOT / Bureau of Transportation Statistics
- ~5.8 million flight records
- Three CSV files: `flights.csv` (~600 MB), `airlines.csv`, `airports.csv`

Potential fields include:

- Flight date
- Airline or carrier
- Flight number
- Origin airport
- Destination airport
- Scheduled departure and arrival time
- Actual departure and arrival time
- Departure delay
- Arrival delay
- Taxi-out and taxi-in time
- Air time
- Flight distance
- Cancellation indicator and cancellation reason
- Diversion indicator

### Supporting datasets

- **OurAirports:** Airport metadata — name, city, state, country, latitude, longitude. Source: https://ourairports.com/data/
- **Airline metadata:** Carrier name and code (included in Kaggle dataset).
- **Weather data (extension only):** Temperature, precipitation, wind, visibility from NOAA ISD or ASOS.
- **Calendar information:** Weekends, holidays, and seasons (derived from flight date).

### Other available sources (for reference or extension)

| Dataset/source | What it provides | Access |
|---|---|---|
| BTS Airline On-Time Performance | U.S. domestic flight records with full detail | [BTS On-Time](https://transtats.bts.gov/ONTIME/) |
| BTS Flight Delays and Delay Causes | Monthly delay-cause summaries | [BTS Delay Causes](https://www.transtats.bts.gov/OT_Delay/) |
| NOAA Integrated Surface Database | Hourly weather observations | [NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) |
| OpenSky Network | Live and historical aircraft positions | [OpenSky](https://opensky-network.org/data/) |

### Dataset selection strategy

Begin with the Kaggle 2015 dataset and OurAirports. Additional sources should be added only after the core pipeline works.

### Data quality checks

- Validate required columns and data types.
- Check for duplicate flight records.
- Identify impossible times and negative or extreme values.
- Measure missingness by field and source.
- Document assumptions used to handle missing or ambiguous data.

---

## 9. Functional Modules

### Module 1: Data ingestion `[Core]` (Colab)

Loads source CSVs into PySpark DataFrames. Records row counts, schemas, and basic statistics.

### Module 2: Data cleaning and ETL `[Core]` (Colab)

Performs schema enforcement, missing-value handling, code standardization, deduplication, and derived-column creation (`is_delayed`, `delay_category`, `time_of_day`, `season`).

### Module 3: RDD and MapReduce demonstration `[Core]` (Colab)

Demonstrates foundational distributed computing concepts:
- Create RDD from flight data
- `map()` and `reduceByKey()` to count delays per airline (MapReduce pattern)
- Compare execution and verbosity with equivalent DataFrame operation
- Document: why Spark DataFrames are preferred over raw RDDs for production analytics

### Module 4: SparkSQL demonstration `[Core]` (Colab)

- Register cleaned DataFrames as temporary SQL views
- Run SQL queries: `SELECT airline, AVG(departure_delay) ... GROUP BY airline ORDER BY ...`
- Show equivalent DataFrame API code side-by-side
- Demonstrate that SparkSQL and DataFrame API produce identical results

### Module 5: Flight operations analytics `[Core]` (Colab)

Calculates delay, cancellation, diversion, distance, and punctuality metrics across different dimensions.

### Module 6: Airline performance `[Core]` (Colab)

Ranks airlines using measures such as average delay, median delay, delay rate, cancellation rate, and sample size.

### Module 7: Airport intelligence `[Core]` (Colab)

Identifies airports with high delay frequency, long average delays, peak congestion periods, and unusual operational patterns.

### Module 8: Route intelligence `[Core]` (Colab)

Analyzes origin-destination pairs, route reliability, average delay, cancellation risk, and route volume.

### Module 9: Machine learning — Classification `[Core]` (Colab)

Predicts whether a flight will be delayed beyond 15 minutes using Spark MLlib (Logistic Regression + Random Forest).

### Module 10: Machine learning — Clustering `[Core]` (Colab)

Groups airports into operational profiles using K-Means clustering on features like average delay, flight volume, cancellation rate, and peak-hour congestion. Outputs cluster labels and centroids.

### Module 11: MongoDB push `[Core]` (Colab)

Pushes all aggregated DataFrames, ML results, and cluster assignments to MongoDB Atlas collections.

### Module 12: Dashboard and Streamlit app `[Core]` (Local)

Connects to MongoDB Atlas, reads precomputed documents, renders interactive pages with Plotly.

### Module 13: Streaming analytics demonstration `[Extension]` (Colab)

Demonstrates how incoming flight events could be processed in near real time using Spark Structured Streaming with a file source (simulated from historical CSV). Computes rolling delay counts and airport congestion indicators. No Kafka required — file source is sufficient for syllabus demonstration.

### Module 14: Weather enrichment `[Extension]` (Colab)

Joins flight records with NOAA weather observations by airport and time window. Adds weather-aware features to ML model.

---

## 10. Spark Concepts Demonstrated

This section maps specific Spark syllabus topics to where they appear in the project notebooks.

### RDD concepts

```python
# Create RDD from flight data
flights_rdd = flights_df.rdd

# MapReduce-style: count delayed flights per airline
delay_counts = flights_rdd \
    .filter(lambda row: row['DEPARTURE_DELAY'] is not None and row['DEPARTURE_DELAY'] > 15) \
    .map(lambda row: (row['AIRLINE'], 1)) \
    .reduceByKey(lambda a, b: a + b) \
    .collect()
```

### DataFrame equivalent

```python
# Same result using DataFrame API
delay_counts_df = flights_df \
    .filter(col("DEPARTURE_DELAY") > 15) \
    .groupBy("AIRLINE") \
    .count() \
    .orderBy(desc("count"))
```

### SparkSQL equivalent

```python
flights_df.createOrReplaceTempView("flights")

spark.sql("""
    SELECT AIRLINE, COUNT(*) as delay_count
    FROM flights
    WHERE DEPARTURE_DELAY > 15
    GROUP BY AIRLINE
    ORDER BY delay_count DESC
""")
```

### Lazy evaluation and DAG

- Transformations (`filter`, `groupBy`, `join`) are lazy — they build a DAG but do not execute.
- Actions (`count`, `collect`, `show`, `write`) trigger execution of the DAG.
- Spark UI screenshots will be captured to show DAG visualization for a representative job.

### Fault tolerance

- RDDs maintain lineage information — if a partition is lost, Spark recomputes it from the lineage graph.
- DataFrames inherit the same fault tolerance through the Catalyst optimizer's logical plan.
- This contrasts with HDFS replication-based fault tolerance (data redundancy vs computation redundancy).

---

## 11. NoSQL Concepts Demonstrated

### RDBMS vs NoSQL justification

| Aspect | RDBMS | MongoDB (NoSQL) | Why MongoDB suits this project |
|---|---|---|---|
| Schema | Fixed, predefined | Flexible, per-document | Aggregation outputs vary by dimension — airline docs differ from route docs |
| Scaling | Vertical | Horizontal (sharding) | Designed for distributed serving at scale |
| Query pattern | Complex joins | Denormalized reads | Dashboard reads precomputed docs — no joins needed at query time |
| Data format | Tables and rows | JSON/BSON documents | Natural fit for API/dashboard consumption |

### CAP Theorem analysis

MongoDB Atlas operates as a **CP system** by default:
- **Consistency:** All reads from the primary return the latest write.
- **Partition tolerance:** The replica set continues operating if network partitions occur.
- **Availability tradeoff:** During a primary election (after primary failure), writes are briefly unavailable.

For this project's read-heavy dashboard workload, CP behavior is appropriate — stale data from a dashboard is worse than a brief pause.

### NoSQL database types (documented comparison)

| Type | Example | Data model | Best for |
|---|---|---|---|
| **Key-Value** | Redis, DynamoDB | Simple key → value pairs | Caching, session storage, simple lookups |
| **Document** | MongoDB | JSON-like documents with nested fields | Flexible schemas, API serving, content management |
| **Column-Family** | Cassandra, HBase | Rows with dynamic column families | Time-series data, write-heavy workloads, wide tables |
| **Graph** | Neo4j | Nodes and edges with properties | Social networks, recommendation engines, relationship queries |

**Why Document DB for this project:** Dashboard queries retrieve pre-shaped documents (airline profile, airport summary, route metrics). Each document is self-contained — no joins needed. This matches the document model perfectly.

### MongoDB data modeling

- **Denormalized design:** Each collection stores pre-aggregated, dashboard-ready documents. No runtime joins.
- **Collection-per-dimension:** Separate collections for airline metrics, airport metrics, route metrics, time trends, ML results.
- **Indexing:** Index on `airline_code`, `airport_code`, `origin`+`destination` for fast lookups.

### Sharding and replication

- **Replication:** MongoDB Atlas automatically maintains a 3-node replica set (primary + 2 secondaries). Provides fault tolerance and read scaling.
- **Sharding concept:** For this dataset size, sharding is not needed. However, the project report documents how sharding would work — `airport_code` as shard key for `airport_metrics`, range-based distribution across shards.

---

## 12. Analytics Features

### Core KPIs

- Total flights
- On-time flight percentage
- Average departure delay
- Average arrival delay
- Median delay
- Cancellation rate
- Diversion rate
- Total delayed flights
- Most affected airports
- Most affected routes

### Delay analysis

- Delay distribution by airline
- Delay trends by month, day, and hour
- Departure delay versus arrival delay
- Percentage of flights delayed beyond 15, 30, or 60 minutes
- Delay cause breakdown where cause fields are available

### Airline analysis

- Airline punctuality ranking
- Airline delay-rate comparison
- Cancellation and diversion comparison
- Performance by airport and route
- Volume-adjusted comparisons to avoid misleading rankings based on very small samples

### Airport analysis

- Origin and destination airport rankings
- Geographic heatmap of delays
- Peak operating periods
- Airport-level cancellation patterns
- Comparison of small and large airports
- Airport cluster assignments from K-Means (operational profiles)

### Route analysis

- Most frequently operated routes
- Most delayed routes
- Most reliable routes
- Average route delay by season
- Route volume and operational risk comparison

### What-if and decision-support views

- Select an airline, airport, or route to inspect its profile.
- Compare two airlines or airports.
- Filter by date range, season, time window, and delay threshold.
- Show recommended periods or routes with lower historical delay risk.

---

## 13. Streaming Analytics Demonstration `[Extension]`

### Purpose

Demonstrate real-time vs batch processing concepts from the syllabus without requiring Kafka infrastructure.

### Approach

Simulate a stream of flight events by writing batches of rows from historical data into a monitored directory. Spark Structured Streaming reads new files as they appear.

### Implementation

```python
# Structured Streaming — read new CSV files as they arrive
streaming_df = spark.readStream \
    .schema(flights_schema) \
    .csv("/content/streaming_input/")

# Rolling delay counts per airline
delay_stream = streaming_df \
    .filter(col("DEPARTURE_DELAY") > 15) \
    .groupBy("AIRLINE") \
    .count()

# Output to console (or memory sink for notebook display)
query = delay_stream.writeStream \
    .outputMode("complete") \
    .format("console") \
    .start()
```

### Batch vs streaming comparison (documented)

| Aspect | Batch (core pipeline) | Streaming (this demo) |
|---|---|---|
| Data source | Complete historical CSV | Simulated arriving files |
| Processing trigger | Manual job execution | Automatic on new data |
| Latency | Minutes (full dataset) | Seconds (per micro-batch) |
| Use case | Historical analytics, ML training | Live monitoring, alerting |
| Complexity | Lower | Higher (state management, checkpointing) |

---

## 14. Machine Learning Module

### Use case 1: Classification — Delay prediction `[Core]`

**Target:** Predict whether a flight will be delayed by more than 15 minutes (binary).

**Features (known before departure only):**
- Airline
- Origin airport
- Destination airport
- Month and season
- Day of week
- Scheduled departure hour
- Flight distance
- Historical airport delay rate
- Historical airline delay rate
- Route-level historical delay rate

**Feature leakage prevention — do NOT use:**
- Actual departure/arrival time
- Departure delay (leaks arrival delay)
- Taxi-out/taxi-in time
- Actual elapsed time
- Any field only known after departure

**Candidate models:**
- Logistic Regression (MLlib)
- Random Forest (MLlib)

**Evaluation metrics:**
- Accuracy
- Precision
- Recall
- F1 score
- Confusion matrix
- ROC-AUC
- Baseline comparison (always predict "not delayed")

**Class imbalance handling:**
- ~80% flights are on-time
- Use class weights in model training
- Stratified train/test split
- Report precision/recall/F1 alongside accuracy

### Use case 2: Clustering — Airport operational profiles `[Core]`

**Goal:** Group airports into clusters based on operational characteristics. Demonstrates unsupervised learning from the syllabus.

**Features:**
- Average departure delay
- Delay rate (% flights >15 min late)
- Total flight volume
- Cancellation rate
- Peak-hour congestion ratio
- Number of airlines serving the airport

**Algorithm:** K-Means (Spark MLlib)

**Evaluation:**
- Silhouette score
- Within-cluster sum of squares (WCSS) / elbow method
- Manual inspection of cluster centroids — do clusters map to interpretable airport types?

**Expected clusters (example):**
- Cluster A: High-traffic hub, moderate delays (ATL, ORD, DFW)
- Cluster B: Medium airports, low delays (BNA, SAN)
- Cluster C: Small regional airports, variable performance
- Cluster D: High-delay airports regardless of size

**Dashboard integration:** Airport page shows cluster assignment and cluster profile descriptions.

### ML deliverable

The dashboard can show:
- Predicted delay probability and risk category (low / medium / high)
- Main factors associated with the prediction (feature importance chart)
- Model performance summary (F1, accuracy, confusion matrix)
- Airport cluster map — color-coded by cluster assignment
- Cluster profile descriptions

---

## 15. Dashboard Pages

### Page 1: Executive overview

- KPI cards (total flights, on-time %, avg delay, cancellation rate)
- Overall delay trend (monthly line chart)
- Top 5 most/least delayed airlines
- Top 5 most/least delayed airports
- Date and airline filters

### Page 2: Airline performance

- Airline ranking table (sortable)
- Average and median delay comparison
- Cancellation rate
- Monthly performance trend
- Airline-specific filters

### Page 3: Airport intelligence

- Airport map (Plotly scatter_mapbox with cluster color coding)
- Delay and cancellation rankings
- Peak delay hours heatmap
- Origin versus destination analysis
- Airport cluster profile descriptions

### Page 4: Route intelligence

- Route search (origin → destination)
- Most delayed routes
- Most reliable routes
- Route volume and delay comparison scatter

### Page 5: Delay causes and patterns

- Delay-cause breakdown (carrier, weather, NAS, security, late aircraft)
- Seasonal and weekly patterns
- Hour-of-day analysis
- Distribution of delay durations

### Page 6: Delay prediction

- Input form for a hypothetical flight (airline, origin, destination, month, day, hour, distance)
- Predicted delay risk (low / medium / high)
- Model metrics summary
- Feature importance chart

### Page 7: Streaming monitor `[Extension]`

- Current event count
- Rolling delay rate
- Airport alert table
- Recent incoming events

---

## 16. Example User Flow

1. The user opens the executive overview.
2. The user selects a date range and airline.
3. KPI cards update to show the selected airline's performance.
4. The user opens the airport page and identifies airports with the highest delay rates.
5. The user notices airport cluster assignments — sees that hub airports cluster together.
6. The user selects a route to inspect reliability and historical trends.
7. The user enters a hypothetical flight's details in the prediction page.
8. The platform displays the estimated delay risk and explains the main contributing factors.
9. The user uses the results to compare operating choices or investigate a performance issue.

---

## 17. MongoDB Collection Schemas

### `airline_metrics`
```json
{
  "airline_code": "AA",
  "airline_name": "American Airlines",
  "total_flights": 537264,
  "on_time_pct": 79.2,
  "avg_dep_delay": 12.4,
  "avg_arr_delay": 8.7,
  "median_delay": 3.0,
  "cancellation_rate": 1.8,
  "delay_rate": 20.8
}
```

### `airport_metrics`
```json
{
  "airport_code": "ATL",
  "airport_name": "Hartsfield-Jackson Atlanta International",
  "lat": 33.6407,
  "lon": -84.4277,
  "total_flights": 346023,
  "avg_delay": 10.2,
  "delay_rate": 22.1,
  "cancellation_rate": 1.2,
  "peak_delay_hour": 17,
  "cluster_id": 0,
  "cluster_label": "High-traffic hub, moderate delays"
}
```

### `route_metrics`
```json
{
  "origin": "LAX",
  "destination": "SFO",
  "total_flights": 12543,
  "avg_delay": 8.9,
  "delay_rate": 18.3,
  "cancellation_rate": 0.9,
  "reliability_rank": 42
}
```

### `time_trends`
```json
{
  "dimension": "monthly",
  "period": "2015-06",
  "total_flights": 503897,
  "avg_delay": 14.2,
  "delay_rate": 24.1,
  "cancellation_rate": 1.1
}
```

### `delay_distribution`
```json
{
  "delay_bucket": "15-30 min",
  "count": 324891,
  "percentage": 12.3
}
```

### `ml_classification_results`
```json
{
  "model_name": "random_forest",
  "accuracy": 0.82,
  "precision": 0.61,
  "recall": 0.54,
  "f1": 0.57,
  "roc_auc": 0.78,
  "baseline_accuracy": 0.80,
  "feature_importances": {
    "historical_airport_delay_rate": 0.18,
    "scheduled_hour": 0.15,
    "airline_code": 0.13
  }
}
```

### `ml_clustering_results`
```json
{
  "model_name": "kmeans",
  "k": 4,
  "silhouette_score": 0.62,
  "wcss": 1423.7,
  "cluster_centroids": [
    {"cluster_id": 0, "label": "High-traffic hub", "avg_delay": 11.2, "volume": 280000, "cancellation_rate": 1.5},
    {"cluster_id": 1, "label": "Medium reliable", "avg_delay": 7.1, "volume": 45000, "cancellation_rate": 0.8}
  ]
}
```

### `overall_kpis`
```json
{
  "total_flights": 5819811,
  "on_time_pct": 80.1,
  "avg_dep_delay": 10.3,
  "avg_arr_delay": 7.8,
  "cancellation_rate": 1.5,
  "diversion_rate": 0.2
}
```

---

## 18. Ethics, Privacy, and Bias Considerations

This section addresses Unit 6 syllabus requirements.

### Privacy and security

- **No passenger PII:** The dataset contains flight operational data only — no passenger names, booking data, or personal information.
- **MongoDB Atlas security:** Access controlled via database user credentials, IP whitelist, TLS encryption in transit. Connection string stored in environment variables, not hardcoded.
- **API key management:** Kaggle API key stored in `~/.kaggle/`, MongoDB URI in `.env` file (excluded from Git via `.gitignore`).

### Ethical concerns

- **Fair airline comparison:** Airlines with few flights may appear at ranking extremes. Volume-adjusted metrics and minimum flight count thresholds prevent misleading rankings.
- **Historical data limitations:** 2015 data does not reflect current airline operations. The platform should not be used for real booking decisions — it is an academic analytics tool.
- **Delay attribution:** Delay causes (carrier, weather, NAS) are reported by airlines themselves — potential self-reporting bias exists. This limitation is documented.
- **Data licensing:** Kaggle dataset is public domain (U.S. government data). OurAirports data is open data. Usage terms are respected.

### Bias in analytics and ML

- **Class imbalance bias:** ~80% on-time flights. A model predicting "not delayed" for everything achieves 80% accuracy but is useless. Precision, recall, F1, and confusion matrix prevent this false conclusion.
- **Geographic bias:** U.S. domestic flights only. Results do not generalize to international operations.
- **Temporal bias:** Single year (2015). Seasonal patterns may not hold across years. Documented as limitation.
- **Small-sample bias:** Airports or routes with very few flights produce unreliable statistics. Minimum sample size filter applied before ranking.
- **Algorithmic fairness:** Clustering may group small airports unfavorably due to high variance from low flight counts. Cluster assignments include volume context to prevent misinterpretation.

---

## 19. Colab Notebook Structure

```
notebooks/
├── 01_data_loading.ipynb            # Load CSVs, initial exploration, schema inspection
├── 02_data_cleaning_etl.ipynb       # PySpark ETL, write cleaned Parquet to Drive
├── 03_rdd_mapreduce_demo.ipynb      # RDD operations, MapReduce-style delay counting
├── 04_sparksql_demo.ipynb           # SparkSQL queries, comparison with DataFrame API
├── 05_aggregations.ipynb            # All Spark aggregation jobs (airline, airport, route, time)
├── 06_ml_classification.ipynb       # Feature engineering, delay prediction, evaluation
├── 07_ml_clustering.ipynb           # Airport clustering, silhouette score, cluster profiles
├── 08_mongodb_push.ipynb            # Push all results to MongoDB Atlas
├── 09_streaming_demo.ipynb          # [Extension] Spark Structured Streaming demonstration
└── 10_spark_concepts_doc.ipynb      # Lazy eval, DAG, fault tolerance — documented with examples
```

## Local Project Structure

```
airline-intel-platform/
├── app/
│   ├── app.py                       # Streamlit main entry
│   ├── pages/
│   │   ├── 01_overview.py
│   │   ├── 02_airlines.py
│   │   ├── 03_airports.py
│   │   ├── 04_routes.py
│   │   ├── 05_delay_causes.py
│   │   └── 06_prediction.py
│   ├── utils/
│   │   ├── db.py                    # MongoDB Atlas connection
│   │   └── charts.py               # Plotly chart helpers
│   └── requirements.txt
├── docs/
│   ├── project_report.md            # Full report with syllabus concept discussions
│   ├── data_dictionary.md           # Field definitions and assumptions
│   └── nosql_comparison.md          # RDBMS vs NoSQL, CAP theorem, NoSQL types
├── .env                             # MongoDB URI (not committed)
├── .gitignore
└── README.md
```

---

## 20. Eight-Week Project Timeline

| Week | Planned work | Expected output |
|---|---|---|
| 1 | Confirm scope, select datasets, define KPIs, set up Colab + MongoDB Atlas + local repo | Project plan, environment ready, Kaggle data loaded in Colab |
| 2 | Explore data, inspect schemas, create data dictionary, build sample ETL pipeline | Data understanding report, initial ingestion notebook |
| 3 | Implement full cleaning, validation, transformation. RDD and MapReduce demo notebook. SparkSQL demo. | Reproducible ETL pipeline, Parquet on Drive, RDD/SparkSQL notebooks |
| 4 | Build Spark aggregations for airline, airport, route, and time-based analytics | Curated analytical datasets, MongoDB push working |
| 5 | Build Streamlit dashboard structure, connect to MongoDB, add filters and core visualizations | Working dashboard with 4-5 pages |
| 6 | Implement ML classification (delay prediction) and clustering (airport profiles), evaluate results | ML notebooks, results pushed to MongoDB, prediction page in dashboard |
| 7 | Add delay causes page, streaming demo notebook, spark concepts documentation, optimize | Near-final platform, extension notebooks |
| 8 | Testing, documentation, screenshots, ethics/bias writeup, presentation, demo rehearsal | Final submission and presentation |

### Milestones

- **End of Week 2:** Data and scope confirmed, ETL started
- **End of Week 4:** ETL and core analytics working, MongoDB populated
- **End of Week 5:** Dashboard MVP available
- **End of Week 6:** ML models evaluated and integrated
- **End of Week 8:** Final integrated demonstration

---

## 21. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Dataset is too large for Colab RAM | Slow processing or crashed runtime | Use Parquet, partition data, avoid `.toPandas()` on full DataFrame. Set `spark.driver.memory` to 4g max |
| Colab runtime resets | Lost intermediate work | Save cleaned Parquet and aggregation results to Google Drive after each notebook |
| Dataset contains missing or inconsistent values | Incorrect metrics | Establish data dictionary and validation rules early |
| Scope becomes too ambitious | Incomplete final product | Modules marked `[Extension]` are cut first. Core modules are the priority |
| MongoDB Atlas connection issues from Colab | Blocked push | Add `0.0.0.0/0` to Atlas IP whitelist (Colab IPs are dynamic) |
| Dashboard queries are slow | Poor user experience | All heavy computation done in Colab. Dashboard reads precomputed docs only |
| Airline rankings are misleading | Weak conclusions | Include sample sizes, use volume-adjusted metrics, set minimum flight count thresholds |
| ML model has class imbalance | Misleading accuracy | Report precision, recall, F1, confusion matrix, and baseline comparison |
| Streaming demo fails | Missing syllabus coverage | Use simple file source instead of Kafka. Document batch vs streaming comparison even if demo is minimal |

---

## 22. Evaluation Strategy

### Data engineering evaluation

- Does the pipeline run from raw CSV to curated Parquet to MongoDB?
- Are transformations reproducible?
- Are schemas and assumptions documented?
- Are invalid and missing records handled consistently?
- Does Spark process the data correctly?

### Spark concepts evaluation

- Are RDD operations demonstrated with MapReduce pattern?
- Is SparkSQL used alongside DataFrame API?
- Is lazy evaluation and DAG explained with examples?
- Is fault tolerance documented?
- Is Spark vs MapReduce comparison clear?

### NoSQL evaluation

- Is the RDBMS vs NoSQL justification documented?
- Is the CAP theorem applied to MongoDB?
- Are other NoSQL types discussed with rationale for choosing Document DB?
- Is data modeling in MongoDB explained?
- Are sharding and replication concepts documented?

### Performance evaluation

- Compare processing time for sample vs full dataset.
- Record execution time before and after partitioning or caching.
- Explain why Parquet and precomputed summaries improve dashboard access.

### Analytics evaluation

- Validate selected KPIs against independently calculated samples.
- Check that filters update results correctly.
- Confirm that charts use consistent definitions and units.
- Test edge cases such as empty selections and missing values.

### Dashboard evaluation

- Can a new user find the main KPIs quickly?
- Are labels, legends, and units clear?
- Are comparisons fair and interpretable?
- Does the interface support the intended user flow?

### Machine learning evaluation

- Classification: Train/test split, compare to baseline, report F1 and confusion matrix.
- Clustering: Silhouette score, elbow plot, interpretable cluster descriptions.
- Feature leakage check: No post-departure features used.
- Explain limitations of historical prediction.

### Ethics and bias evaluation

- Are privacy and security measures documented?
- Are bias sources identified and mitigated?
- Is fair comparison methodology explained?
- Are data licensing and attribution correct?

### Demonstration evaluation

The final demo should show one complete path:

```text
Raw CSV → PySpark ETL → Spark Aggregations → MongoDB Atlas → Streamlit Dashboard → Prediction + Clustering
```

---

## 23. Suggested Deliverables

- Project proposal and requirements document
- Dataset inventory and data dictionary
- Source data or documented acquisition instructions
- Colab notebooks (ETL, RDD demo, SparkSQL demo, aggregations, ML classification, ML clustering, MongoDB push, streaming demo, Spark concepts)
- Curated Parquet outputs (on Google Drive)
- MongoDB Atlas collections
- Interactive Streamlit dashboard
- Project report with syllabus concept discussions (5 V's, MapReduce vs Spark, RDBMS vs NoSQL, CAP theorem, NoSQL types, sharding/replication, lazy evaluation, DAG, fault tolerance, batch vs streaming, ethics, bias)
- Testing and performance report
- Final presentation and live demonstration
- README explaining how to run the system

---

## 24. Scope Control Rules

Modules and pages are marked `[Core]` or `[Extension]`.

1. **All `[Core]` modules ship first.** No extension work begins until core is complete and stable.
2. **If time runs short, cut `[Extension]` modules.** Streaming demo and weather enrichment are first to go.
3. **Dashboard page 7 (streaming monitor) only if streaming demo works.** Otherwise, document batch vs streaming comparison in the report without a live dashboard page.
4. **Syllabus concepts that cannot be fully implemented are still documented.** HDFS architecture, sharding at scale, and Kafka streaming are explained in the project report even if not implemented live.
5. **Working demo of 5 pages > broken demo of 7.** Quality over quantity.

---

## 25. Future Enhancements

If the core platform is completed early, the following extensions can be considered:

- Real-time flight tracking using OpenSky or another live source
- Weather-aware delay prediction using NOAA data
- Dynamic alerting for airport congestion
- Recommendation engine for lower-risk travel windows or routes
- Passenger-impact estimation based on delay duration
- Cost estimation for operational disruptions
- Aircraft turnaround-time analysis
- Model monitoring and drift detection
- Cloud deployment using managed storage and distributed compute
- Natural-language querying of operational metrics
- More advanced time-series forecasting for airport delay rates

These enhancements should not replace core deliverables.

---

## 26. Recommended Minimum Viable Product

To protect the timeline, the minimum viable product should include:

- Kaggle 2015 flight dataset loaded and explored
- Documented PySpark ETL pipeline
- Cleaned data stored in Parquet on Google Drive
- RDD and MapReduce demonstration notebook
- SparkSQL demonstration notebook
- Airline, airport, route, and time-based analytics
- At least five dashboard pages connected to MongoDB Atlas
- Interactive filters
- One classification model (delay prediction) with evaluation
- One clustering model (airport profiles) with evaluation
- Basic documentation including 5 V's, NoSQL justification, CAP theorem, Spark concepts
- Ethics and bias section in project report

Streaming, weather enrichment, and advanced models should be added only after this baseline is working.

---

## Appendix A — Loading Kaggle Data into Colab

### Method 1: Kaggle API (recommended)

```python
# Install Kaggle CLI
!pip install -q kaggle

# Upload kaggle.json API key
# (kaggle.com → Account → Create New API Token → downloads kaggle.json)
from google.colab import files
files.upload()  # upload kaggle.json

# Move key to correct location
!mkdir -p ~/.kaggle
!mv kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json

# Download dataset
!kaggle datasets download -d usdot/flight-delays -p /content/data --unzip

# Verify
!ls -lh /content/data/
# Expected: flights.csv (~600MB), airlines.csv, airports.csv
```

### Method 2: Google Drive (fallback)

```python
# Download dataset manually from Kaggle to PC, upload zip to Google Drive

from google.colab import drive
drive.mount('/content/drive')

!cp /content/drive/MyDrive/flight-delays.zip /content/data/
!cd /content/data && unzip -o flight-delays.zip

!ls -lh /content/data/
```

### After loading — PySpark setup

```python
!pip install -q pyspark

from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("AirlineIntel") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

flights_df = spark.read.csv("/content/data/flights.csv", header=True, inferSchema=True)
airlines_df = spark.read.csv("/content/data/airlines.csv", header=True, inferSchema=True)
airports_df = spark.read.csv("/content/data/airports.csv", header=True, inferSchema=True)

print(f"Flights: {flights_df.count():,} rows, {len(flights_df.columns)} columns")
flights_df.printSchema()
flights_df.show(5)
```

### Colab gotchas

1. **Runtime resets = data gone.** Files in `/content/` are wiped. Mount Google Drive and save cleaned Parquet there.
2. **Don't `inferSchema` every run.** After first run, define schema explicitly for faster loads.
3. **Save intermediate results to Drive.** `cleaned_df.write.parquet("/content/drive/MyDrive/airline-project/cleaned/")`
4. **RAM limit:** Free Colab = ~12GB RAM. Don't `.toPandas()` the full flights DataFrame.
5. **Spark driver memory:** `4g` max on free Colab. Higher causes OOM.

---

## Appendix B — MongoDB Atlas Setup

### One-time Atlas setup

1. Go to https://cloud.mongodb.com → Create free account
2. Create free cluster (M0 Sandbox — shared, free forever)
3. Set database user + password
4. Add `0.0.0.0/0` to IP whitelist (Colab IPs are dynamic)
5. Get connection string from Atlas dashboard

### Colab push example

```python
!pip install -q pymongo

from pymongo import MongoClient

# Store URI in Colab secrets or environment variable
MONGO_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"

client = MongoClient(MONGO_URI)
db = client["airline_intel"]

# Push airline metrics
airline_metrics = airline_summary_df.toPandas().to_dict("records")
db["airline_metrics"].drop()
db["airline_metrics"].insert_many(airline_metrics)
print(f"Pushed {len(airline_metrics)} airline documents")
```

### Streamlit read example (local)

```python
import streamlit as st
from pymongo import MongoClient
import os

@st.cache_resource
def get_db():
    client = MongoClient(os.getenv("MONGO_URI"))
    return client["airline_intel"]

db = get_db()
airlines = list(db["airline_metrics"].find({}, {"_id": 0}))
```

---

## 27. Conclusion

The Airline Operations Intelligence Platform is a practical and academically comprehensive Big Data Analytics project. It connects distributed data processing, ETL, NoSQL, analytics, machine learning (both classification and clustering), and visualization in one coherent system while demonstrating all six syllabus units — including RDD and MapReduce concepts, SparkSQL, Spark architecture, NoSQL data modeling and the CAP theorem, streaming analytics, and ethical considerations.

The Colab + MongoDB Atlas + Streamlit architecture provides a practical, zero-infrastructure-overhead development path for a solo developer while still demonstrating the full range of Big Data concepts required by the course.

The immediate next step is to set up the Colab environment, load the Kaggle dataset, and begin the ETL pipeline.
