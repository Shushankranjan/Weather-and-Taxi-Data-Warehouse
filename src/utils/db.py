"""
DuckDB connection manager and schema utilities.

Handles database connections, schema creation, and SQL execution
with proper resource management.
"""

import duckdb
from pathlib import Path
from contextlib import contextmanager

from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_project_root() -> Path:
    """Return the project root directory (two levels up from this file)."""
    return Path(__file__).resolve().parent.parent.parent


@contextmanager
def get_connection(db_path: str = None):
    """
    Context manager for DuckDB connections.

    Args:
        db_path: Path to the DuckDB database file (relative to project root).
                 Defaults to 'data/warehouse.duckdb'.

    Yields:
        duckdb.DuckDBPyConnection
    """
    if db_path is None:
        db_path = str(get_project_root() / "data" / "warehouse.duckdb")
    else:
        # Make relative paths relative to project root
        p = Path(db_path)
        if not p.is_absolute():
            db_path = str(get_project_root() / db_path)

    # Ensure the parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def create_schemas(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Create the raw, staging, and marts schemas if they don't exist.
    """
    for schema in ("raw", "staging", "marts"):
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        logger.info(f"  Schema '{schema}' ready")


def execute_sql_file(
    conn: duckdb.DuckDBPyConnection, sql_path: str
) -> None:
    """
    Read and execute a SQL file against the given connection.

    Args:
        conn: Active DuckDB connection.
        sql_path: Path to a .sql file (relative to project root or absolute).
    """
    p = Path(sql_path)
    if not p.is_absolute():
        p = get_project_root() / p

    sql = p.read_text(encoding="utf-8")
    logger.info(f"  Executing SQL: {p.name}")

    # Split on semicolons to handle multi-statement files,
    # but skip empty statements
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for statement in statements:
        conn.execute(statement)


def run_sql_query(
    conn: duckdb.DuckDBPyConnection, query: str
) -> list:
    """
    Run a SQL query and return results as a list of tuples.
    """
    return conn.execute(query).fetchall()


def get_row_count(
    conn: duckdb.DuckDBPyConnection, schema: str, table: str
) -> int:
    """Return the row count for a schema.table."""
    result = conn.execute(
        f"SELECT COUNT(*) FROM {schema}.{table}"
    ).fetchone()
    return result[0] if result else 0
