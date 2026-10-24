"""
Structured logger for the ETL pipeline.

Provides consistent, structured logging with timings and row counts
across all pipeline stages (NFR-4: Observability).
"""

import logging
import sys
import time
from functools import wraps


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Create a structured logger with consistent formatting.

    Args:
        name: Logger name (usually __name__ of the calling module).
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def log_stage(stage_name: str):
    """
    Decorator that logs the start, end, and duration of a pipeline stage.

    Usage:
        @log_stage("Extract Taxi Data")
        def extract_taxi(...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            logger.info(f"▶ STAGE START: {stage_name}")
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(
                    f"✔ STAGE DONE:  {stage_name} "
                    f"(elapsed: {elapsed:.1f}s)"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(
                    f"✖ STAGE FAIL:  {stage_name} "
                    f"(elapsed: {elapsed:.1f}s) — {type(e).__name__}: {e}"
                )
                raise

        return wrapper

    return decorator


def log_row_count(logger: logging.Logger, table: str, count: int) -> None:
    """Log a row count for a specific table."""
    logger.info(f"  ↳ {table}: {count:,} rows")
