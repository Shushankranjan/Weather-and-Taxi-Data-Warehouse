# Product Requirements Document (PRD)

## Project: Weather & Taxi Batch ETL Data Warehouse

| Field | Detail |
|---|---|
| **Owner** | You (solo data engineer / learner) |
| **Status** | Draft v1.0 |
| **Type** | Portfolio / learning project |
| **Estimated duration** | 4 to 6 weeks (part-time) |
| **Last updated** | 24 Oct 2026 |

---

## 1. Overview

### 1.1 Summary
Build an end-to-end **batch ETL pipeline** that extracts NYC taxi trip data and historical weather data from public sources, loads it raw into a local analytical database (DuckDB), cleans and transforms it with SQL, and models it into a **star schema** that supports analytics queries such as "How does rain affect taxi demand?"

### 1.2 Problem Statement
Raw data from public sources is messy, inconsistent, and spread across different formats and APIs. Analysts cannot answer cross-source questions (trips vs. weather) without a clean, joined, well-modeled dataset. This project builds the data infrastructure that makes those questions easy to answer.

### 1.3 Why This Project
- Teaches the fundamentals every data engineer needs: Python, SQL, data modeling, pipeline design, testing, and orchestration.
- Runs entirely on a laptop for free.
- Produces a concrete, demonstrable portfolio piece (code, architecture diagram, analysis results).

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Automate extraction of taxi trip data and weather data from public sources.
2. Store unmodified source data in a **raw layer** for traceability.
3. Clean, validate, and standardize data in a **staging layer**.
4. Build a **star schema** (fact and dimension tables) in a **marts layer**.
5. Make the pipeline **idempotent** (re-running it never creates duplicates) and **re-runnable** for any date range.
6. Include automated **data quality checks** and **unit tests**.
7. Answer at least 5 business questions with SQL.
8. Document everything well enough that another person can reproduce the project.

### 2.2 Non-Goals (out of scope for v1)
- Real-time or streaming ingestion.
- Cloud deployment (Snowflake, BigQuery, Redshift). Possible future extension.
- Machine learning or forecasting models.
- A production-grade BI tool. Basic charts or a notebook are enough.
- Handling data volumes beyond what one laptop can process.

---

## 3. Target User and Use Cases

### 3.1 Primary User
The project owner, a beginner data engineer building skills and a portfolio.

### 3.2 Secondary Users (hypothetical consumers of the data)
- **Data analyst**: wants clean tables to query with SQL.
- **Business stakeholder**: wants answers to demand and revenue questions.
- **Recruiter / reviewer**: evaluates code quality, structure, and documentation.

### 3.3 Business Questions the Warehouse Must Answer
1. What are the busiest hours and days of the week for taxi trips?
2. Do trip counts drop or rise on rainy days compared with dry days?
3. How does temperature affect average trip distance and fare?
4. Which pickup zones generate the most trips and revenue?
5. What is the average tip percentage by payment type?
6. (Stretch) What is the month-over-month trend in trips and revenue?

---

## 4. Data Sources

### 4.1 NYC TLC Yellow Taxi Trip Records
- **Provider:** NYC Taxi & Limousine Commission (public).
- **Format:** Parquet files, one per month.
- **Granularity:** One row per trip.
- **Key fields:** pickup/dropoff datetime, pickup/dropoff location ID, passenger count, trip distance, fare amount, tip amount, total amount, payment type.
- **Volume:** Roughly 2 to 3 million rows per month.
- **Scope for v1:** 3 to 6 months of data (configurable).

### 4.2 NYC Taxi Zone Lookup
- **Format:** CSV.
- **Purpose:** Maps location IDs to borough, zone name, and service zone.
- **Use:** Source for the location dimension.

### 4.3 Open-Meteo Historical Weather API
- **Provider:** Open-Meteo (free, no API key).
- **Format:** JSON over HTTP.
- **Granularity:** Hourly.
- **Location:** New York City (single latitude/longitude point).
- **Key fields:** temperature, precipitation, rain, snowfall, wind speed, weather code.

> **Note:** Verify the current download URLs and API parameters from each provider's documentation before starting, as they can change.

---

## 5. Functional Requirements

### 5.1 Extraction
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Download taxi Parquet files for a configurable list of year-months. | Must |
| FR-2 | Download the taxi zone lookup CSV. | Must |
| FR-3 | Fetch hourly weather data for a configurable date range from Open-Meteo. | Must |
| FR-4 | Skip downloads when the file already exists locally (avoid re-downloading). | Should |
| FR-5 | Retry failed HTTP requests with backoff (at least 3 attempts). | Should |
| FR-6 | Log every extraction (source, file, row count, timestamp). | Must |

### 5.2 Load (Raw Layer)
| ID | Requirement | Priority |
|---|---|---|
| FR-7 | Load source data into `raw` schema tables with no business transformations. | Must |
| FR-8 | Add metadata columns: `_source_file`, `_loaded_at`. | Must |
| FR-9 | Loading must be idempotent: re-loading the same month replaces that month's rows, never duplicates them. | Must |

### 5.3 Transform (Staging Layer)
| ID | Requirement | Priority |
|---|---|---|
| FR-10 | Cast columns to correct data types (timestamps, numerics, integers). | Must |
| FR-11 | Rename columns to consistent `snake_case` names. | Must |
| FR-12 | Remove exact duplicate rows. | Must |
| FR-13 | Filter invalid trips: negative or zero fares, zero distance, dropoff before pickup, pickup outside the target date range, passenger count outside 0 to 8. | Must |
| FR-14 | Standardize weather timestamps to the same timezone as taxi data (America/New_York). | Must |
| FR-15 | Write rejected rows to a `rejected_trips` table with a rejection reason. | Should |

### 5.4 Model (Marts Layer: Star Schema)
| ID | Requirement | Priority |
|---|---|---|
| FR-16 | Build `dim_date` covering the full date range (date, day of week, month, quarter, year, is_weekend). | Must |
| FR-17 | Build `dim_time` (hour of day, time-of-day bucket such as morning, afternoon, evening, night). | Should |
| FR-18 | Build `dim_location` from the taxi zone lookup (location_id, borough, zone, service_zone). | Must |
| FR-19 | Build `dim_payment_type` (code and description). | Must |
| FR-20 | Build `dim_weather` at hourly grain (hour timestamp, temperature, precipitation, wind speed, weather category such as clear, rain, snow). | Must |
| FR-21 | Build `fact_trips` at one row per trip with foreign keys to all dimensions and numeric measures (distance, fare, tip, total, duration in minutes). | Must |
| FR-22 | Use surrogate keys for dimensions. | Should |

### 5.5 Data Quality and Testing
| ID | Requirement | Priority |
|---|---|---|
| FR-23 | Check no nulls in primary keys and required foreign keys. | Must |
| FR-24 | Check uniqueness of dimension keys. | Must |
| FR-25 | Check referential integrity: every `fact_trips` foreign key exists in its dimension. | Must |
| FR-26 | Check row count reconciliation: raw rows = staging rows + rejected rows. | Must |
| FR-27 | Check value ranges (for example, fare and distance within plausible bounds). | Should |
| FR-28 | Fail the pipeline run loudly if a "Must" check fails. | Must |
| FR-29 | Unit tests (pytest) for Python extraction and helper functions. | Should |

### 5.6 Orchestration and Execution
| ID | Requirement | Priority |
|---|---|---|
| FR-30 | A single command runs the full pipeline (`python run_pipeline.py --start 2025-01 --end 2025-03`). | Must |
| FR-31 | Each stage can run on its own (extract, load, transform, model, test). | Should |
| FR-32 | Phase 2: schedule the pipeline in Apache Airflow as a DAG with task dependencies, retries, and alerts. | Could |
| FR-33 | Phase 2: migrate SQL transformations to dbt models with built-in tests and documentation. | Could |

### 5.7 Analytics Layer
| ID | Requirement | Priority |
|---|---|---|
| FR-34 | Provide a `/sql/analysis/` folder with one query file per business question. | Must |
| FR-35 | Provide a notebook or script that charts at least 3 results. | Should |

---

## 6. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | **Idempotency** | Running the pipeline twice for the same period yields identical results. |
| NFR-2 | **Reproducibility** | A new user can clone the repo, install dependencies, and run the pipeline by following the README. |
| NFR-3 | **Performance** | Full run for 3 months (about 9M rows) completes in under 15 minutes on a laptop with 8 GB RAM. |
| NFR-4 | **Observability** | Structured logs per stage with timings and row counts. |
| NFR-5 | **Maintainability** | Modular code, no hard-coded paths or credentials, configuration in a single file. |
| NFR-6 | **Security** | No secrets committed to Git. Use `.env` and `.gitignore`. |
| NFR-7 | **Cost** | Total cost is zero. Only free tools and public data. |
| NFR-8 | **Portability** | Runs on Windows, macOS, and Linux. |

---

## 7. Architecture

### 7.1 Data Flow

```
 +------------------+     +------------------+
 | NYC TLC Parquet  |     | Open-Meteo API   |
 | + Zone CSV       |     | (JSON, hourly)   |
 +--------+---------+     +--------+---------+
          |                        |
          v                        v
     [ EXTRACT: Python scripts (requests) ]
          |                        |
          v                        v
 +-------------------------------------------+
 |  data/landing/  (downloaded files)        |
 +----------------------+--------------------+
                        |
                        v   [ LOAD ]
 +-------------------------------------------+
 |  DuckDB  schema: raw                      |
 |  raw.taxi_trips, raw.weather, raw.zones   |
 +----------------------+--------------------+
                        |
                        v   [ TRANSFORM: SQL ]
 +-------------------------------------------+
 |  DuckDB  schema: staging                  |
 |  stg_trips, stg_weather, rejected_trips   |
 +----------------------+--------------------+
                        |
                        v   [ MODEL: SQL ]
 +-------------------------------------------+
 |  DuckDB  schema: marts (star schema)      |
 |  fact_trips + dim_date, dim_time,         |
 |  dim_location, dim_payment_type,          |
 |  dim_weather                              |
 +----------------------+--------------------+
                        |
                        v
        [ ANALYSIS: SQL queries + charts ]
```

### 7.2 Layers

| Layer | Schema | Purpose |
|---|---|---|
| Landing | files on disk | Raw downloaded files, untouched |
| Raw | `raw` | Source data loaded as-is plus metadata |
| Staging | `staging` | Cleaned, typed, deduplicated, validated |
| Marts | `marts` | Business-ready star schema |

### 7.3 Technology Stack

| Purpose | Tool | Notes |
|---|---|---|
| Language | Python 3.11+ | Extraction, orchestration script |
| Database | DuckDB | Embedded, fast analytics, no server |
| Data libraries | pandas, pyarrow, requests | Reading Parquet, calling APIs |
| Transformations | SQL (Phase 1), dbt-duckdb (Phase 2) | |
| Orchestration | Python CLI (Phase 1), Airflow (Phase 2) | |
| Testing | pytest, custom SQL checks | |
| Version control | Git + GitHub | |
| Visualization | Jupyter or Matplotlib/Plotly | |
| Diagrams | draw.io or Mermaid | For README |

---

## 8. Data Model (Star Schema)

### 8.1 Fact Table: `marts.fact_trips`
**Grain:** one row per taxi trip.

| Column | Type | Description |
|---|---|---|
| trip_key | BIGINT | Surrogate primary key |
| pickup_date_key | INT | FK to dim_date |
| pickup_time_key | INT | FK to dim_time |
| pickup_location_key | INT | FK to dim_location |
| dropoff_location_key | INT | FK to dim_location |
| payment_type_key | INT | FK to dim_payment_type |
| weather_key | INT | FK to dim_weather (matched on pickup hour) |
| pickup_datetime | TIMESTAMP | Trip start |
| dropoff_datetime | TIMESTAMP | Trip end |
| passenger_count | INT | Passengers |
| trip_distance_miles | DOUBLE | Distance |
| trip_duration_minutes | DOUBLE | Derived |
| fare_amount | DECIMAL(10,2) | Base fare |
| tip_amount | DECIMAL(10,2) | Tip |
| total_amount | DECIMAL(10,2) | Total charged |

### 8.2 Dimension Tables

**`marts.dim_date`**: date_key, full_date, day_of_week, day_name, week_of_year, month, month_name, quarter, year, is_weekend

**`marts.dim_time`**: time_key, hour_24, hour_label, time_of_day_bucket

**`marts.dim_location`**: location_key, location_id, borough, zone, service_zone

**`marts.dim_payment_type`**: payment_type_key, payment_type_code, payment_type_description

**`marts.dim_weather`**: weather_key, observation_hour, temperature_c, precipitation_mm, rain_mm, snowfall_cm, wind_speed_kmh, weather_category

### 8.3 Weather Category Rules (example)
- `snow` if snowfall > 0
- `rain` if precipitation > 0.1 mm and no snow
- `clear` otherwise

---

## 9. Project Structure

```
nyc-taxi-weather-dwh/
├── README.md
├── PRD.md
├── requirements.txt
├── .gitignore
├── .env.example
├── config/
│   └── config.yaml
├── data/
│   ├── landing/          # downloaded files (gitignored)
│   └── warehouse.duckdb  # database file (gitignored)
├── src/
│   ├── extract/
│   │   ├── taxi_extractor.py
│   │   ├── weather_extractor.py
│   │   └── zone_extractor.py
│   ├── load/
│   │   └── load_raw.py
│   ├── utils/
│   │   ├── logger.py
│   │   └── db.py
│   └── run_pipeline.py
├── sql/
│   ├── staging/
│   │   ├── stg_trips.sql
│   │   └── stg_weather.sql
│   ├── marts/
│   │   ├── dim_date.sql
│   │   ├── dim_time.sql
│   │   ├── dim_location.sql
│   │   ├── dim_payment_type.sql
│   │   ├── dim_weather.sql
│   │   └── fact_trips.sql
│   ├── tests/
│   │   └── data_quality_checks.sql
│   └── analysis/
│       ├── q1_busiest_hours.sql
│       ├── q2_rain_vs_dry.sql
│       ├── q3_temperature_effect.sql
│       ├── q4_top_zones.sql
│       └── q5_tip_by_payment.sql
├── tests/
│   └── test_extractors.py
├── notebooks/
│   └── analysis.ipynb
├── docs/
│   └── architecture.png
└── airflow/              # Phase 2
    └── dags/
        └── taxi_weather_dag.py
```

---

## 10. Milestones and Timeline

| Phase | Weeks | Deliverables | Done when |
|---|---|---|---|
| **M0: Setup** | Week 1 (days 1-2) | Python, VS Code, DuckDB installed. GitHub repo created. Folder structure in place. | `pip install -r requirements.txt` works and repo is pushed |
| **M1: Extract** | Week 1 (days 3-7) | Extractors for taxi, zones, and weather with logging and retries | Files appear in `data/landing/` for chosen months |
| **M2: Load raw** | Week 2 | Idempotent raw loader with metadata columns | Re-running load gives the same row counts |
| **M3: Staging** | Week 2-3 | Cleaning SQL, rejected-rows table, reconciliation check | raw = staging + rejected |
| **M4: Marts** | Week 3-4 | All dimensions and `fact_trips` built | Joins return correct results, FK checks pass |
| **M5: Quality and tests** | Week 4 | Data quality SQL checks, pytest tests, pipeline fails on bad data | All checks pass on a clean run |
| **M6: Analysis** | Week 5 | 5 SQL answers plus 3 charts | Insights written in README |
| **M7: Polish** | Week 5-6 | README, architecture diagram, clean commits | A stranger can reproduce the project |
| **M8 (Phase 2)** | Week 6+ | dbt models and Airflow DAG | Daily scheduled run works |

---

## 11. Success Metrics and Acceptance Criteria

### 11.1 Success Metrics
| Metric | Target |
|---|---|
| Pipeline success rate on clean data | 100% |
| Duplicate rows after re-run | 0 |
| Data quality checks passing | 100% of "Must" checks |
| Business questions answered | At least 5 |
| Reconciliation | raw rows = staging + rejected rows |
| Runtime for 3 months of data | Under 15 minutes |
| README reproducibility | New user can run it in under 30 minutes |

### 11.2 Acceptance Criteria (definition of done)
- [ ] One command runs extract, load, transform, model, and tests end to end.
- [ ] Running the pipeline twice produces identical table row counts.
- [ ] All dimension keys are unique and non-null.
- [ ] Every foreign key in `fact_trips` resolves to a dimension row.
- [ ] Rejected rows are stored with reasons.
- [ ] At least 5 analysis queries run and return sensible results.
- [ ] README contains an architecture diagram, setup steps, and example results.
- [ ] No secrets or large data files are committed to Git.

---

## 12. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Source URL or API format changes | Medium | Medium | Keep URLs in config, handle errors clearly, document the check date |
| Laptop runs out of memory on large files | Medium | Medium | Let DuckDB read Parquet directly, process month by month |
| Timezone mismatch between taxi and weather data | High | High | Convert everything to America/New_York in staging, add a test |
| Dirty data (bad dates, negative fares) | High | Medium | Validation rules plus a `rejected_trips` table |
| Duplicate loads on re-run | Medium | High | Delete-then-insert per month, idempotency test |
| Scope creep (adding Airflow, dbt, cloud too early) | High | Medium | Finish Phase 1 fully before starting Phase 2 |
| Losing motivation | Medium | High | Small weekly milestones and commit often |

---

## 13. Assumptions and Dependencies

**Assumptions**
- Public data sources remain freely available.
- A laptop with at least 8 GB RAM and 10 GB free disk space is available.
- The owner has basic computer skills and is willing to learn Python and SQL along the way.

**Dependencies**
- Internet access for downloads.
- Python 3.11+, DuckDB, pandas, pyarrow, requests, pytest.
- GitHub account.

---

## 14. Learning Outcomes

By completing this project you will have practiced:
- Python scripting, HTTP APIs, and file handling.
- SQL: joins, window functions, CTEs, aggregations, date handling.
- Data modeling: star schema, grain, surrogate keys, fact vs. dimension tables.
- Pipeline design: layers, idempotency, logging, error handling.
- Data quality testing and reconciliation.
- Git workflow and technical documentation.
- (Phase 2) dbt and Airflow fundamentals.

---

## 15. Future Enhancements (Backlog)

1. Migrate transformations to **dbt** with tests and generated docs.
2. Orchestrate with **Airflow** on a daily schedule.
3. Add more sources: green taxi, for-hire vehicles, holidays, events.
4. Incremental loading and slowly changing dimensions (SCD Type 2).
5. Move to a cloud warehouse (BigQuery, Snowflake) and cloud storage (S3 or GCS).
6. Containerize with **Docker**.
7. Add CI with **GitHub Actions** to run tests on every push.
8. Build a dashboard in Metabase, Superset, or Power BI.
9. Convert to a streaming version using Kafka and Spark Structured Streaming.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| **ETL** | Extract, Transform, Load |
| **Idempotent** | Running an operation many times gives the same result as running it once |
| **Grain** | What one row in a table represents |
| **Fact table** | Table of measurable events (trips) |
| **Dimension table** | Table of descriptive context (date, location) |
| **Star schema** | A fact table surrounded by dimension tables |
| **Surrogate key** | An artificial unique ID used instead of a natural key |
| **Staging** | Intermediate layer where data is cleaned |
| **Reconciliation** | Verifying row counts match between layers |
| **DAG** | Directed acyclic graph, a workflow of ordered tasks |
