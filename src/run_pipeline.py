"""
Main Pipeline Runner.

Single command to run the full ETL pipeline (FR-30).
Each stage can also be run independently (FR-31).

Usage:
    # Full pipeline for configured months:
    python -m src.run_pipeline

    # Full pipeline with custom date range:
    python -m src.run_pipeline --start 2024-01 --end 2024-03

    # Run a single stage:
    python -m src.run_pipeline --stage extract
    python -m src.run_pipeline --stage load
    python -m src.run_pipeline --stage transform
    python -m src.run_pipeline --stage model
    python -m src.run_pipeline --stage test
    python -m src.run_pipeline --stage analyze
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

from src.utils.logger import get_logger, log_stage
from src.utils.config import load_config
from src.utils.db import get_connection, create_schemas, execute_sql_file, get_row_count
from src.extract.taxi_extractor import extract_taxi_data
from src.extract.zone_extractor import extract_zone_data
from src.extract.weather_extractor import extract_weather_data
from src.load.load_raw import load_raw

logger = get_logger(__name__)


def _override_config_dates(config: dict, start: str, end: str) -> dict:
    """
    Override the configured months and weather date range
    based on CLI --start and --end arguments.

    Args:
        config: Configuration dictionary.
        start: Start month (YYYY-MM).
        end: End month (YYYY-MM).

    Returns:
        Updated configuration dictionary.
    """
    from datetime import date

    start_date = datetime.strptime(start, "%Y-%m")
    end_date = datetime.strptime(end, "%Y-%m")

    # Generate list of months
    months = []
    current = start_date
    while current <= end_date:
        months.append(current.strftime("%Y-%m"))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    config["sources"]["taxi"]["months"] = months

    # Update weather date range to cover full months
    config["sources"]["weather"]["start_date"] = f"{start}-01"
    # End date: last day of end month
    if end_date.month == 12:
        last_day = date(end_date.year + 1, 1, 1)
    else:
        last_day = date(end_date.year, end_date.month + 1, 1)
    from datetime import timedelta
    last_day = last_day - timedelta(days=1)
    config["sources"]["weather"]["end_date"] = last_day.isoformat()

    logger.info(f"  Date range: {start} to {end}")
    logger.info(f"  Months: {months}")
    logger.info(
        f"  Weather range: {config['sources']['weather']['start_date']} "
        f"to {config['sources']['weather']['end_date']}"
    )

    return config


@log_stage("Extract")
def run_extract(config: dict) -> None:
    """Run all extractors."""
    extract_taxi_data(config)
    extract_zone_data(config)
    extract_weather_data(config)


@log_stage("Transform (Staging)")
def run_transform(config: dict) -> None:
    """Run staging SQL transforms."""
    db_path = config["paths"]["database"]
    sql_dir = Path("sql/staging")

    with get_connection(db_path) as conn:
        create_schemas(conn)
        # Order matters: stg_trips and rejected_trips both read from raw
        execute_sql_file(conn, sql_dir / "stg_trips.sql")
        execute_sql_file(conn, sql_dir / "rejected_trips.sql")
        execute_sql_file(conn, sql_dir / "stg_weather.sql")

        # Log row counts
        for table in ["stg_trips", "rejected_trips", "stg_weather"]:
            count = get_row_count(conn, "staging", table)
            logger.info(f"  ↳ staging.{table}: {count:,} rows")


@log_stage("Model (Marts)")
def run_model(config: dict) -> None:
    """Build the star schema in the marts layer."""
    db_path = config["paths"]["database"]
    sql_dir = Path("sql/marts")

    # Order: dimensions first, then fact table
    sql_files = [
        "dim_date.sql",
        "dim_time.sql",
        "dim_location.sql",
        "dim_payment_type.sql",
        "dim_weather.sql",
        "fact_trips.sql",  # depends on dim_weather
    ]

    with get_connection(db_path) as conn:
        create_schemas(conn)
        for sql_file in sql_files:
            execute_sql_file(conn, sql_dir / sql_file)

        # Log row counts
        for table in [
            "dim_date", "dim_time", "dim_location",
            "dim_payment_type", "dim_weather", "fact_trips",
        ]:
            count = get_row_count(conn, "marts", table)
            logger.info(f"  ↳ marts.{table}: {count:,} rows")


@log_stage("Data Quality Checks")
def run_tests(config: dict) -> bool:
    """
    Run data quality checks. Returns True if all Must checks pass.
    """
    db_path = config["paths"]["database"]
    sql_path = Path("sql/tests/data_quality_checks.sql")

    # Read and split the SQL file into individual check queries
    project_root = Path(__file__).resolve().parent.parent
    full_path = project_root / sql_path
    sql_content = full_path.read_text(encoding="utf-8")

    # Split on semicolons to handle individual check statements
    checks = [s.strip() for s in sql_content.split(";") if s.strip()]

    all_passed = True
    must_failed = False

    with get_connection(db_path) as conn:
        for check_sql in checks:
            check_sql = check_sql.strip().rstrip(";")
            if not check_sql:
                continue
            try:
                result = conn.execute(check_sql).fetchone()
                if result and len(result) >= 3:
                    check_name, priority, failures = result[0], result[1], result[2]
                    status = "✔ PASS" if failures == 0 else "✖ FAIL"
                    logger.info(
                        f"  {status} | {check_name} "
                        f"({priority}) | failures: {failures}"
                    )
                    if failures > 0:
                        all_passed = False
                        if priority == "Must":
                            must_failed = True
            except Exception as e:
                logger.error(f"  ✖ Error running check: {e}")
                logger.error(f"  SQL: {check_sql[:100]}...")
                all_passed = False

    if must_failed:
        logger.error("  ✖ CRITICAL: One or more 'Must' checks FAILED!")
        return False

    if all_passed:
        logger.info("  ✔ All data quality checks passed!")
    else:
        logger.warning("  ⚠ Some 'Should' checks failed (non-critical)")

    return not must_failed


@log_stage("Analysis Queries")
def run_analyze(config: dict) -> None:
    """Run all analysis queries and print results."""
    db_path = config["paths"]["database"]
    analysis_dir = Path(__file__).resolve().parent.parent / "sql" / "analysis"

    with get_connection(db_path) as conn:
        for sql_file in sorted(analysis_dir.glob("*.sql")):
            logger.info(f"\n  === {sql_file.stem} ===")
            sql = sql_file.read_text(encoding="utf-8")

            # Strip comments for cleaner execution
            statements = [
                s.strip() for s in sql.split(";")
                if s.strip() and not s.strip().startswith("--")
            ]

            for statement in statements:
                try:
                    result = conn.execute(statement)
                    columns = [desc[0] for desc in result.description]
                    rows = result.fetchall()

                    # Print as a simple table
                    logger.info(f"  Columns: {', '.join(columns)}")
                    for row in rows[:10]:  # Limit output
                        logger.info(f"  {row}")
                    if len(rows) > 10:
                        logger.info(f"  ... and {len(rows) - 10} more rows")
                except Exception as e:
                    logger.error(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Weather & Taxi Data Warehouse ETL Pipeline"
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start month (YYYY-MM), e.g., 2024-01",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End month (YYYY-MM), e.g., 2024-03",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["extract", "load", "transform", "model", "test", "analyze"],
        help="Run only a specific stage (FR-31)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Override dates if provided
    if args.start and args.end:
        config = _override_config_dates(config, args.start, args.end)
    elif args.start or args.end:
        parser.error("Both --start and --end are required together")

    pipeline_start = time.time()
    logger.info("=" * 60)
    logger.info("  Weather & Taxi Data Warehouse Pipeline")
    logger.info(f"  Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    stages = {
        "extract": lambda: run_extract(config),
        "load": lambda: load_raw(config),
        "transform": lambda: run_transform(config),
        "model": lambda: run_model(config),
        "test": lambda: run_tests(config),
        "analyze": lambda: run_analyze(config),
    }

    if args.stage:
        # Run a single stage
        stages[args.stage]()
    else:
        # Run the full pipeline
        run_extract(config)
        load_raw(config)
        run_transform(config)
        run_model(config)

        # FR-28: Fail the pipeline if Must checks fail
        checks_passed = run_tests(config)
        if not checks_passed:
            logger.error("Pipeline FAILED: data quality checks did not pass.")
            sys.exit(1)

        run_analyze(config)

    elapsed = time.time() - pipeline_start
    logger.info("=" * 60)
    logger.info(f"  Pipeline completed in {elapsed:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
