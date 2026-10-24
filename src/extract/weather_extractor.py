"""
Open-Meteo Historical Weather Data Extractor.

Fetches hourly weather data from the Open-Meteo API for
a configurable date range and NYC coordinates.
Free API, no key required.
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

from src.utils.logger import get_logger, log_stage
from src.utils.config import load_config

logger = get_logger(__name__)


@log_stage("Extract Weather Data")
def extract_weather_data(config: dict = None) -> Path:
    """
    Fetch hourly weather data from Open-Meteo and save as Parquet.

    The API returns a JSON payload with hourly arrays. We convert
    these into a DataFrame and save as Parquet for efficient loading.

    Args:
        config: Configuration dictionary. Loaded from config.yaml if None.

    Returns:
        Path to the saved weather Parquet file.
    """
    if config is None:
        config = load_config()

    weather_cfg = config["sources"]["weather"]
    extract_cfg = config["extraction"]
    landing_dir = Path(config["paths"]["landing_dir"])

    dest = landing_dir / "weather_hourly.parquet"

    # FR-4: Skip if already exists
    if dest.exists():
        logger.info(f"  ⏭ Already exists, skipping: {dest}")
        return dest

    # Build the API request parameters
    params = {
        "latitude": weather_cfg["latitude"],
        "longitude": weather_cfg["longitude"],
        "start_date": weather_cfg["start_date"],
        "end_date": weather_cfg["end_date"],
        "hourly": ",".join(weather_cfg["hourly_variables"]),
        "timezone": weather_cfg["timezone"],
    }

    url = weather_cfg["base_url"]
    max_retries = extract_cfg["max_retries"]
    backoff = extract_cfg["retry_backoff_seconds"]
    timeout = extract_cfg["request_timeout_seconds"]

    # Fetch with retry
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"  Fetching weather data (attempt {attempt}/{max_retries})"
            )
            logger.info(
                f"  Date range: {weather_cfg['start_date']} "
                f"to {weather_cfg['end_date']}"
            )
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"  Attempt {attempt} failed: {type(e).__name__}: {e}"
            )
            if attempt < max_retries:
                wait = backoff * (2 ** (attempt - 1))
                logger.info(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"  ✖ All {max_retries} attempts failed")
                raise

    # Parse the hourly data into a DataFrame
    hourly = data.get("hourly", {})

    if not hourly or "time" not in hourly:
        raise ValueError(
            "Open-Meteo response missing 'hourly' or 'time' field. "
            f"Response keys: {list(data.keys())}"
        )

    df = pd.DataFrame(
        {
            "observation_time": hourly["time"],
            "temperature_c": hourly.get("temperature_2m"),
            "precipitation_mm": hourly.get("precipitation"),
            "rain_mm": hourly.get("rain"),
            "snowfall_cm": hourly.get("snowfall"),
            "wind_speed_kmh": hourly.get("wind_speed_10m"),
            "weather_code": hourly.get("weather_code"),
        }
    )

    # Convert observation_time to proper datetime
    df["observation_time"] = pd.to_datetime(df["observation_time"])

    # Save as Parquet
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, index=False, engine="pyarrow")

    logger.info(f"  ✔ Saved: {dest}")
    logger.info(f"  ↳ Weather rows: {len(df):,}")
    logger.info(
        f"  ↳ Date range: {df['observation_time'].min()} "
        f"to {df['observation_time'].max()}"
    )

    # Also save the raw JSON for traceability
    json_dest = landing_dir / "weather_hourly_raw.json"
    with open(json_dest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"  ✔ Raw JSON saved: {json_dest}")

    return dest


if __name__ == "__main__":
    extract_weather_data()
