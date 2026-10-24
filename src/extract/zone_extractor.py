"""
NYC Taxi Zone Lookup Extractor.

Downloads the taxi zone lookup CSV from the NYC TLC public dataset.
"""

from pathlib import Path

from src.extract.taxi_extractor import download_file
from src.utils.logger import get_logger, log_stage
from src.utils.config import load_config

logger = get_logger(__name__)


@log_stage("Extract Zone Data")
def extract_zone_data(config: dict = None) -> Path:
    """
    Download the taxi zone lookup CSV.

    Args:
        config: Configuration dictionary. Loaded from config.yaml if None.

    Returns:
        Path to the downloaded CSV file.
    """
    if config is None:
        config = load_config()

    zones_cfg = config["sources"]["zones"]
    extract_cfg = config["extraction"]
    landing_dir = Path(config["paths"]["landing_dir"])

    url = zones_cfg["url"]
    dest = landing_dir / zones_cfg["filename"]

    # Skip if already exists (FR-4)
    if dest.exists():
        logger.info(f"  ⏭ Already exists, skipping: {dest}")
        return dest

    return download_file(
        url=url,
        dest_path=dest,
        max_retries=extract_cfg["max_retries"],
        backoff_seconds=extract_cfg["retry_backoff_seconds"],
        timeout=extract_cfg["request_timeout_seconds"],
    )


if __name__ == "__main__":
    extract_zone_data()
