"""
NYC Yellow Taxi Trip Data Extractor.

Downloads monthly Parquet files from the NYC TLC public dataset.
Implements retry with backoff (FR-5), skip-if-exists (FR-4),
and structured logging (FR-6).
"""

import time
from pathlib import Path

import requests
from tqdm import tqdm

from src.utils.logger import get_logger, log_stage
from src.utils.config import load_config

logger = get_logger(__name__)


def download_file(
    url: str,
    dest_path: Path,
    max_retries: int = 3,
    backoff_seconds: int = 2,
    timeout: int = 60,
    chunk_size: int = 8192,
) -> Path:
    """
    Download a file from a URL with retry and backoff.

    Args:
        url: Source URL.
        dest_path: Local destination file path.
        max_retries: Number of retry attempts on failure.
        backoff_seconds: Base wait time between retries (doubles each time).
        timeout: HTTP request timeout in seconds.
        chunk_size: Bytes per chunk for streaming download.

    Returns:
        Path to the downloaded file.

    Raises:
        requests.exceptions.RequestException: If all retries are exhausted.
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"  Downloading (attempt {attempt}/{max_retries}): {url}"
            )
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(dest_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=dest_path.name,
                    disable=total_size == 0,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
                        pbar.update(len(chunk))

            logger.info(f"  ✔ Saved: {dest_path}")
            return dest_path

        except requests.exceptions.RequestException as e:
            logger.warning(
                f"  Attempt {attempt} failed: {type(e).__name__}: {e}"
            )
            if attempt < max_retries:
                wait = backoff_seconds * (2 ** (attempt - 1))
                logger.info(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"  ✖ All {max_retries} attempts failed for {url}")
                raise


@log_stage("Extract Taxi Data")
def extract_taxi_data(config: dict = None) -> list[Path]:
    """
    Download taxi trip Parquet files for all configured months.

    Args:
        config: Configuration dictionary. Loaded from config.yaml if None.

    Returns:
        List of paths to downloaded Parquet files.
    """
    if config is None:
        config = load_config()

    taxi_cfg = config["sources"]["taxi"]
    extract_cfg = config["extraction"]
    landing_dir = Path(config["paths"]["landing_dir"])

    base_url = taxi_cfg["base_url"]
    file_pattern = taxi_cfg["file_pattern"]
    months = taxi_cfg["months"]

    downloaded_files = []

    for year_month in months:
        filename = file_pattern.format(year_month=year_month)
        url = f"{base_url}/{filename}"
        dest = landing_dir / filename

        # FR-4: Skip if file already exists
        if dest.exists():
            logger.info(f"  ⏭ Already exists, skipping: {dest}")
            downloaded_files.append(dest)
            continue

        path = download_file(
            url=url,
            dest_path=dest,
            max_retries=extract_cfg["max_retries"],
            backoff_seconds=extract_cfg["retry_backoff_seconds"],
            timeout=extract_cfg["request_timeout_seconds"],
            chunk_size=extract_cfg["chunk_size_bytes"],
        )
        downloaded_files.append(path)

    logger.info(f"  Total taxi files: {len(downloaded_files)}")
    return downloaded_files


if __name__ == "__main__":
    extract_taxi_data()
