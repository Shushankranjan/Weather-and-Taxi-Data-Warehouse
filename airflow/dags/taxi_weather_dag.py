"""
Apache Airflow DAG: NYC Weather & Taxi Batch ETL Pipeline.

Phase 2 extension (FR-32).
Orchestrates the batch ETL pipeline on a monthly or daily schedule
with retries, task dependencies, and alerting hooks.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Default DAG arguments
default_args = {
    "owner": "data-engineer",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="weather_taxi_batch_etl",
    default_args=default_args,
    description="End-to-End NYC Taxi & Weather Data Warehouse Pipeline",
    schedule_interval="@monthly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "duckdb", "taxi", "weather"],
) as dag:

    # Stage 1: Extraction
    extract_task = BashOperator(
        task_id="extract_sources",
        bash_command="python -m src.run_pipeline --stage extract",
    )

    # Stage 2: Load Raw
    load_raw_task = BashOperator(
        task_id="load_raw_tables",
        bash_command="python -m src.run_pipeline --stage load",
    )

    # Stage 3: Staging Transformations
    staging_task = BashOperator(
        task_id="transform_staging",
        bash_command="python -m src.run_pipeline --stage transform",
    )

    # Stage 4: Star Schema Modeling
    model_marts_task = BashOperator(
        task_id="model_star_schema",
        bash_command="python -m src.run_pipeline --stage model",
    )

    # Stage 5: Data Quality Tests
    quality_tests_task = BashOperator(
        task_id="run_quality_checks",
        bash_command="python -m src.run_pipeline --stage test",
    )

    # Stage 6: Analytics & Reporting
    analytics_task = BashOperator(
        task_id="run_analysis_queries",
        bash_command="python -m src.run_pipeline --stage analyze",
    )

    # Define task dependencies (DAG flow)
    extract_task >> load_raw_task >> staging_task >> model_marts_task >> quality_tests_task >> analytics_task
