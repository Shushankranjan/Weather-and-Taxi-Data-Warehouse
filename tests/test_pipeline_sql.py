"""
End-to-end SQL and data warehouse transformation tests.

Validates schemas, staging rules, rejected trips logic, star schema
modeling, and data quality check queries against a test DuckDB database.
"""

from pathlib import Path
import duckdb
import pytest

from src.utils.db import create_schemas, execute_sql_file, run_sql_query, get_project_root


@pytest.fixture
def test_db():
    """Create an in-memory DuckDB connection with schemas and mock raw data."""
    conn = duckdb.connect(":memory:")
    create_schemas(conn)

    # 1. Mock raw.zones
    conn.execute("""
        CREATE TABLE raw.zones (
            LocationID INTEGER,
            Borough VARCHAR,
            Zone VARCHAR,
            service_zone VARCHAR,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP
        );
        INSERT INTO raw.zones VALUES
            (1, 'EWR', 'Newark Airport', 'EWR', 'zones.csv', CURRENT_TIMESTAMP),
            (2, 'Queens', 'Jamaica Bay', 'Boro Zone', 'zones.csv', CURRENT_TIMESTAMP),
            (132, 'Queens', 'JFK Airport', 'Airports', 'zones.csv', CURRENT_TIMESTAMP),
            (161, 'Manhattan', 'Midtown Center', 'Yellow Zone', 'zones.csv', CURRENT_TIMESTAMP);
    """)

    # 2. Mock raw.weather
    conn.execute("""
        CREATE TABLE raw.weather (
            observation_time TIMESTAMP,
            temperature_c DOUBLE,
            precipitation_mm DOUBLE,
            rain_mm DOUBLE,
            snowfall_cm DOUBLE,
            wind_speed_kmh DOUBLE,
            weather_code INTEGER,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP
        );
        INSERT INTO raw.weather VALUES
            ('2024-01-15 10:00:00', 5.2, 0.0, 0.0, 0.0, 12.0, 0, 'weather.parquet', CURRENT_TIMESTAMP),
            ('2024-01-15 11:00:00', 4.8, 2.5, 2.5, 0.0, 15.0, 61, 'weather.parquet', CURRENT_TIMESTAMP),
            ('2024-01-15 12:00:00', -1.0, 3.0, 0.0, 2.0, 18.0, 71, 'weather.parquet', CURRENT_TIMESTAMP);
    """)

    # 3. Mock raw.taxi_trips with a mix of valid and invalid records
    conn.execute("""
        CREATE TABLE raw.taxi_trips (
            tpep_pickup_datetime TIMESTAMP,
            tpep_dropoff_datetime TIMESTAMP,
            passenger_count INTEGER,
            trip_distance DOUBLE,
            PULocationID INTEGER,
            DOLocationID INTEGER,
            RatecodeID INTEGER,
            store_and_fwd_flag VARCHAR,
            payment_type INTEGER,
            fare_amount DOUBLE,
            extra DOUBLE,
            mta_tax DOUBLE,
            tip_amount DOUBLE,
            tolls_amount DOUBLE,
            improvement_surcharge DOUBLE,
            total_amount DOUBLE,
            congestion_surcharge DOUBLE,
            airport_fee DOUBLE,
            _source_file VARCHAR,
            _loaded_at TIMESTAMP
        );
        INSERT INTO raw.taxi_trips VALUES
            -- Valid trip 1 (Clear weather hour)
            ('2024-01-15 10:15:00', '2024-01-15 10:30:00', 1, 2.5, 161, 132, 1, 'N', 1, 15.00, 0.5, 0.5, 3.00, 0.0, 1.0, 20.00, 2.5, 0.0, 'taxi.parquet', CURRENT_TIMESTAMP),
            -- Valid trip 2 (Rain weather hour)
            ('2024-01-15 11:05:00', '2024-01-15 11:35:00', 2, 5.0, 132, 161, 1, 'N', 2, 25.00, 0.5, 0.5, 0.00, 6.5, 1.0, 33.50, 2.5, 1.25, 'taxi.parquet', CURRENT_TIMESTAMP),
            -- Invalid: Negative fare
            ('2024-01-15 10:20:00', '2024-01-15 10:30:00', 1, 1.0, 161, 161, 1, 'N', 1, -10.00, 0.0, 0.0, 0.0, 0.0, 0.0, -10.00, 0.0, 0.0, 'taxi.parquet', CURRENT_TIMESTAMP),
            -- Invalid: Zero distance
            ('2024-01-15 10:20:00', '2024-01-15 10:30:00', 1, 0.0, 161, 161, 1, 'N', 1, 10.00, 0.0, 0.0, 0.0, 0.0, 0.0, 10.00, 0.0, 0.0, 'taxi.parquet', CURRENT_TIMESTAMP),
            -- Invalid: Dropoff before pickup
            ('2024-01-15 10:30:00', '2024-01-15 10:10:00', 1, 3.0, 161, 161, 1, 'N', 1, 12.00, 0.0, 0.0, 0.0, 0.0, 0.0, 12.00, 0.0, 0.0, 'taxi.parquet', CURRENT_TIMESTAMP),
            -- Invalid: Excessive passenger count (9)
            ('2024-01-15 10:20:00', '2024-01-15 10:35:00', 9, 2.0, 161, 161, 1, 'N', 1, 15.00, 0.0, 0.0, 0.0, 0.0, 0.0, 15.00, 0.0, 0.0, 'taxi.parquet', CURRENT_TIMESTAMP);
    """)

    yield conn
    conn.close()


def test_staging_transforms_and_reconciliation(test_db):
    """Test staging layer cleaning, rejected table, and row reconciliation (FR-10 to FR-15, FR-26)."""
    root = get_project_root()
    execute_sql_file(test_db, root / "sql" / "staging" / "stg_trips.sql")
    execute_sql_file(test_db, root / "sql" / "staging" / "rejected_trips.sql")
    execute_sql_file(test_db, root / "sql" / "staging" / "stg_weather.sql")

    # 6 total raw rows: 2 valid, 4 invalid
    stg_count = test_db.execute("SELECT COUNT(*) FROM staging.stg_trips").fetchone()[0]
    rej_count = test_db.execute("SELECT COUNT(*) FROM staging.rejected_trips").fetchone()[0]

    assert stg_count == 2
    assert rej_count == 4
    assert stg_count + rej_count == 6

    # Verify weather classification rules (FR-20, Section 8.3)
    from datetime import datetime
    categories = dict(test_db.execute("SELECT observation_hour, weather_category FROM staging.stg_weather").fetchall())
    assert categories[datetime(2024, 1, 15, 10, 0, 0)] == "clear"
    assert categories[datetime(2024, 1, 15, 11, 0, 0)] == "rain"
    assert categories[datetime(2024, 1, 15, 12, 0, 0)] == "snow"


def test_marts_star_schema_and_integrity(test_db):
    """Test star schema creation, surrogate keys, and referential integrity (FR-16 to FR-25)."""
    root = get_project_root()
    # Run staging first
    execute_sql_file(test_db, root / "sql" / "staging" / "stg_trips.sql")
    execute_sql_file(test_db, root / "sql" / "staging" / "rejected_trips.sql")
    execute_sql_file(test_db, root / "sql" / "staging" / "stg_weather.sql")

    # Run marts
    for sql_file in [
        "dim_date.sql",
        "dim_time.sql",
        "dim_location.sql",
        "dim_payment_type.sql",
        "dim_weather.sql",
        "fact_trips.sql",
    ]:
        execute_sql_file(test_db, root / "sql" / "marts" / sql_file)

    # Validate dimensions
    assert test_db.execute("SELECT COUNT(*) FROM marts.dim_time").fetchone()[0] == 24
    assert test_db.execute("SELECT COUNT(*) FROM marts.dim_payment_type").fetchone()[0] >= 6

    # Validate fact table
    fact_count = test_db.execute("SELECT COUNT(*) FROM marts.fact_trips").fetchone()[0]
    assert fact_count == 2

    # Check referential integrity: no missing keys
    missing_locations = test_db.execute("""
        SELECT COUNT(*) FROM marts.fact_trips f
        WHERE NOT EXISTS (SELECT 1 FROM marts.dim_location l WHERE l.location_key = f.pickup_location_key)
    """).fetchone()[0]
    assert missing_locations == 0

    missing_dates = test_db.execute("""
        SELECT COUNT(*) FROM marts.fact_trips f
        WHERE NOT EXISTS (SELECT 1 FROM marts.dim_date d WHERE d.date_key = f.pickup_date_key)
    """).fetchone()[0]
    assert missing_dates == 0


def test_analysis_queries_execute(test_db):
    """Test that all 5 analysis queries execute without syntax errors (FR-34)."""
    root = get_project_root()
    execute_sql_file(test_db, root / "sql" / "staging" / "stg_trips.sql")
    execute_sql_file(test_db, root / "sql" / "staging" / "rejected_trips.sql")
    execute_sql_file(test_db, root / "sql" / "staging" / "stg_weather.sql")
    for sql_file in ["dim_date.sql", "dim_time.sql", "dim_location.sql", "dim_payment_type.sql", "dim_weather.sql", "fact_trips.sql"]:
        execute_sql_file(test_db, root / "sql" / "marts" / sql_file)

    for q_name in [
        "q1_busiest_hours.sql",
        "q2_rain_vs_dry.sql",
        "q3_temperature_effect.sql",
        "q4_top_zones.sql",
        "q5_tip_by_payment.sql",
    ]:
        q_path = root / "sql" / "analysis" / q_name
        sql = q_path.read_text(encoding="utf-8")
        results = test_db.execute(sql).fetchall()
        assert isinstance(results, list)
