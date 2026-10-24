"""
Raw Data Loader.

Loads extracted files into the DuckDB `raw` schema with no business
transformations. Adds metadata columns (_source_file, _loaded_at).
Idempotent via delete-then-insert per month (FR-9).
"""

from pathlib import Path
from datetime import datetime

import duckdb

from src.utils.logger import get_logger, log_stage, log_row_count
from src.utils.config import load_config
from src.utils.db import get_connection, create_schemas

logger = get_logger(__name__)


def _load_taxi_parquet(
    conn: duckdb.DuckDBPyConnection,
    parquet_path: Path,
    year_month: str,
) -> int:
    """
    Load a single taxi Parquet file into raw.taxi_trips.

    Idempotent: deletes existing rows for the same source file
    before inserting.

    Args:
        conn: Active DuckDB connection.
        parquet_path: Path to the Parquet file.
        year_month: The YYYY-MM identifier for this file.

    Returns:
        Number of rows inserted.
    """
    source_file = parquet_path.name
    loaded_at = datetime.now().isoformat()

    # Create table if it doesn't exist (first run)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.taxi_trips AS
        SELECT
            *,
            '' AS _source_file,
            CURRENT_TIMESTAMP AS _loaded_at
        FROM read_parquet($1)
        WHERE 1 = 0
    """, [str(parquet_path)])

    # FR-9: Delete existing rows for this source file (idempotency)
    conn.execute(
        "DELETE FROM raw.taxi_trips WHERE _source_file = $1",
        [source_file],
    )
    logger.info(f"  Purged existing rows for {source_file}")

    # Insert fresh data with metadata columns
    conn.execute("""
        INSERT INTO raw.taxi_trips
        SELECT
            *,
            $2 AS _source_file,
            $3::TIMESTAMP AS _loaded_at
        FROM read_parquet($1)
    """, [str(parquet_path), source_file, loaded_at])

    count = conn.execute(
        "SELECT COUNT(*) FROM raw.taxi_trips WHERE _source_file = $1",
        [source_file],
    ).fetchone()[0]

    logger.info(f"  ✔ Loaded {count:,} rows from {source_file}")
    return count


def _load_zones_csv(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
) -> int:
    """
    Load the taxi zone lookup CSV into raw.zones.

    Idempotent: drops and recreates the table each time.

    Returns:
        Number of rows inserted.
    """
    source_file = csv_path.name
    loaded_at = datetime.now().isoformat()

    conn.execute("DROP TABLE IF EXISTS raw.zones")
    conn.execute("""
        CREATE TABLE raw.zones AS
        SELECT
            *,
            $2 AS _source_file,
            $3::TIMESTAMP AS _loaded_at
        FROM read_csv_auto($1, header=true)
    """, [str(csv_path), source_file, loaded_at])

    count = conn.execute("SELECT COUNT(*) FROM raw.zones").fetchone()[0]
    logger.info(f"  ✔ Loaded {count:,} rows from {source_file}")
    return count


def _load_weather_parquet(
    conn: duckdb.DuckDBPyConnection,
    parquet_path: Path,
) -> int:
    """
    Load the weather Parquet file into raw.weather.

    Idempotent: drops and recreates the table each time.

    Returns:
        Number of rows inserted.
    """
    source_file = parquet_path.name
    loaded_at = datetime.now().isoformat()

    conn.execute("DROP TABLE IF EXISTS raw.weather")
    conn.execute("""
        CREATE TABLE raw.weather AS
        SELECT
            *,
            $2 AS _source_file,
            $3::TIMESTAMP AS _loaded_at
        FROM read_parquet($1)
    """, [str(parquet_path), source_file, loaded_at])

    count = conn.execute("SELECT COUNT(*) FROM raw.weather").fetchone()[0]
    logger.info(f"  ✔ Loaded {count:,} rows from {source_file}")
    return count


@log_stage("Load Raw Data")
def load_raw(config: dict = None) -> dict:
    """
    Load all extracted data into the raw schema.

    Args:
        config: Configuration dictionary. Loaded from config.yaml if None.

    Returns:
        Dictionary with row counts per table.
    """
    if config is None:
        config = load_config()

    landing_dir = Path(config["paths"]["landing_dir"])
    db_path = config["paths"]["database"]
    months = config["sources"]["taxi"]["months"]
    file_pattern = config["sources"]["taxi"]["file_pattern"]

    row_counts = {"taxi_trips": 0, "zones": 0, "weather": 0}

    with get_connection(db_path) as conn:
        create_schemas(conn)

        # Load taxi files
        for year_month in months:
            filename = file_pattern.format(year_month=year_month)
            parquet_path = landing_dir / filename
            if not parquet_path.exists():
                logger.warning(f"  ⚠ Missing taxi file: {parquet_path}")
                continue
            count = _load_taxi_parquet(conn, parquet_path, year_month)
            row_counts["taxi_trips"] += count

        # Load zones
        zones_path = landing_dir / config["sources"]["zones"]["filename"]
        if zones_path.exists():
            row_counts["zones"] = _load_zones_csv(conn, zones_path)
        else:
            logger.warning(f"  ⚠ Missing zones file: {zones_path}")

        # Load weather
        weather_path = landing_dir / "weather_hourly.parquet"
        if weather_path.exists():
            row_counts["weather"] = _load_weather_parquet(conn, weather_path)
        else:
            logger.warning(f"  ⚠ Missing weather file: {weather_path}")

    # Log summary
    logger.info("  --- Raw Layer Summary ---")
    for table, count in row_counts.items():
        log_row_count(logger, f"raw.{table}", count)

    return row_counts


if __name__ == "__main__":
    load_raw()
