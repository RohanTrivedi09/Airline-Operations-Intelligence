# Data Dictionary

Curated dataset: `data/curated/flights.parquet` — **5,819,078 rows x 49 columns**,
partitioned by `month`. Produced by `notebooks/02_data_cleaning_etl.ipynb`.

## Reading the `Leakage` column

`POST` marks a field known only **after** the aircraft departs. Notebook 06 asserts that
none of these enters the delay-prediction model — using `dep_delay` alone would predict
`arr_delay` almost perfectly and produce a meaningless result.

## Null semantics

Every null in this dataset is **structural** — it encodes a fact, and must not be filled:

| Pattern | Cause | Count |
|---|---|---|
| Arrival fields null | Flight cancelled or diverted | 89,884 + 15,187 |
| Delay-cause fields null | Flight arrived on time (<15 min late) | 4,655,639 |
| `cancellation_reason` null | Flight was not cancelled | 5,729,194 |
| `origin_lat`/`origin_lon` null | 3 airports lack coordinates (ECP, PBG, UST) | 5,008 flights |

## Columns

| # | Column | Type | Null % | Leakage | Description |
|---|---|---|---|---|---|
| 1 | `flight_date` | date | 0.00% | - | Date of scheduled departure (local to origin). Derived from YEAR/MONTH/DAY. |
| 2 | `year` | int | 0.00% | - | Always 2015. |
| 3 | `day` | int | 0.00% | - | Day of month, 1-31. |
| 4 | `day_of_week` | int | 0.00% | - | 1=Monday ... 7=Sunday. |
| 5 | `airline_code` | string | 0.00% | - | IATA carrier code, e.g. AA. Join key to airlines.csv. |
| 6 | `airline_name` | string | 0.00% | - | Carrier name, joined from airlines.csv. |
| 7 | `flight_number` | int | 0.00% | - | Carrier flight number. Not unique: one number covers a multi-leg itinerary. |
| 8 | `tail_number` | string | 0.25% | - | Aircraft registration. 0.25% null. Not used as a feature. |
| 9 | `origin` | string | 0.00% | - | Origin airport IATA code. October's DOT numeric codes recovered in notebook 02. |
| 10 | `origin_name` | string | 0.00% | - | Origin airport name. |
| 11 | `origin_city` | string | 0.00% | - | Origin city. |
| 12 | `origin_state` | string | 0.00% | - | Origin US state. |
| 13 | `origin_lat` | double | 0.09% | - | Origin latitude. Null for 3 airports (ECP, PBG, UST). |
| 14 | `origin_lon` | double | 0.09% | - | Origin longitude. Null for the same 3 airports. |
| 15 | `destination` | string | 0.00% | - | Destination airport IATA code, same recovery applied. |
| 16 | `dest_name` | string | 0.00% | - | Destination airport name. |
| 17 | `dest_city` | string | 0.00% | - | Destination city. |
| 18 | `dest_state` | string | 0.00% | - | Destination US state. |
| 19 | `dest_lat` | double | 0.09% | - | Destination latitude. |
| 20 | `dest_lon` | double | 0.09% | - | Destination longitude. |
| 21 | `route` | string | 0.00% | - | origin-destination, e.g. LAX-SFO. Grain of route_metrics. |
| 22 | `sched_dep_min` | int | 0.00% | - | Scheduled departure, minutes since midnight. Converted from HHMM; 2400 maps to 0. |
| 23 | `sched_dep_hour` | int | 0.00% | - | Scheduled departure hour 0-23. Strongest ML feature (importance 0.232). |
| 24 | `actual_dep_min` | int | 1.48% | **POST** | Actual departure, minutes since midnight. Null when cancelled at gate. POST-DEPARTURE. |
| 25 | `sched_arr_min` | int | 0.00% | - | Scheduled arrival, minutes since midnight. |
| 26 | `actual_arr_min` | int | 1.59% | **POST** | Actual arrival, minutes since midnight. Null when cancelled or diverted. POST-DEPARTURE. |
| 27 | `sched_duration` | int | 0.00% | - | Scheduled gate-to-gate minutes. |
| 28 | `actual_duration` | int | 1.81% | **POST** | Actual gate-to-gate minutes. Null unless completed. POST-DEPARTURE. |
| 29 | `air_time` | int | 1.81% | **POST** | Wheels-off to wheels-on minutes. Null unless completed. POST-DEPARTURE. |
| 30 | `distance` | int | 0.00% | - | Great-circle miles. Deterministic per airport pair; used to recover October codes. |
| 31 | `taxi_out` | int | 1.53% | **POST** | Gate to wheels-off minutes. POST-DEPARTURE. |
| 32 | `taxi_in` | int | 1.59% | **POST** | Wheels-on to gate minutes. POST-DEPARTURE. |
| 33 | `status` | string | 0.00% | **POST** | completed | cancelled | diverted. Replaces reliance on null patterns. |
| 34 | `cancelled_after_pushback` | boolean | 0.00% | **POST** | True for the 3,731 flights cancelled after leaving the gate. |
| 35 | `cancellation_reason` | string | 98.46% | **POST** | Carrier | Weather | National Air System | Security. Null unless cancelled. |
| 36 | `dep_delay` | int | 1.48% | **POST** | Actual minus scheduled departure, signed minutes. Negative = early. POST-DEPARTURE. |
| 37 | `arr_delay` | int | 1.81% | **POST** | Actual minus scheduled arrival, signed minutes. Basis of the ML target. POST-DEPARTURE. |
| 38 | `is_delayed` | int | 1.81% | **POST** | 1 if arr_delay >= 15 (US DOT threshold), else 0. Null unless completed. ML TARGET. |
| 39 | `is_delayed_dep` | int | 1.81% | **POST** | 1 if dep_delay >= 15. Null unless completed. POST-DEPARTURE. |
| 40 | `delay_category` | string | 1.81% | **POST** | early | on_time | 15-30 min | 30-60 min | 1-2 hours | 2+ hours. |
| 41 | `delay_carrier` | int | 81.72% | **POST** | Minutes attributed to the carrier. Populated only when arr_delay >= 15. |
| 42 | `delay_weather` | int | 81.72% | **POST** | Minutes attributed to weather. Same condition. |
| 43 | `delay_nas` | int | 81.72% | **POST** | Minutes attributed to the National Air System. Same condition. |
| 44 | `delay_security` | int | 81.72% | **POST** | Minutes attributed to security. Same condition. |
| 45 | `delay_late_aircraft` | int | 81.72% | **POST** | Minutes attributed to a late inbound aircraft. Same condition. Largest single cause (39.8%). |
| 46 | `time_of_day` | string | 0.00% | - | night (<06) | morning (<12) | afternoon (<18) | evening. |
| 47 | `season` | string | 0.00% | - | winter (12,1,2) | spring | summer | autumn. |
| 48 | `is_weekend` | boolean | 0.00% | - | True for Saturday and Sunday. |
| 49 | `month` | int | 0.00% | - | 1-12. Parquet partition key. |

## Source columns dropped in ETL

| Raw column | Reason |
|---|---|
| `YEAR`, `MONTH`, `DAY` | Combined into `flight_date`; `month` retained as partition key |
| `SCHEDULED_DEPARTURE`, `DEPARTURE_TIME`, `SCHEDULED_ARRIVAL`, `ARRIVAL_TIME` | HHMM integers converted to minutes-since-midnight |
| `WHEELS_OFF`, `WHEELS_ON` | Post-departure and unused; taxi times already capture the information |
| `CANCELLED`, `DIVERTED` | Replaced by the single `status` column |
| `ORIGIN_AIRPORT`, `DESTINATION_AIRPORT` | Replaced by `origin`/`destination` after DOT-to-IATA recovery |

## Lineage

```
Dataset/flights.csv        565 MB   5,819,079 rows   (source, unmodified)
  -> data/raw/*.parquet    137 MB   5,819,079 rows   notebook 01, partitioned by month
  -> data/curated/*.parquet 201 MB  5,819,078 rows   notebook 02, 11 cleaning rules
  -> data/marts/*.parquet   276 KB  6,076 documents  notebook 05 + 06 + 07
  -> MongoDB               1.76 MB  6,076 documents  notebook 08
```

One row is lost between raw and curated: the single duplicate business key
(AA803, STT, 2015-08-29 14:35) removed by the deduplication rule.