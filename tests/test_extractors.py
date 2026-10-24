"""
Unit tests for extractor modules.

Tests the extraction helper functions and configuration handling.
Implements FR-29.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.config import load_config
from src.extract.taxi_extractor import download_file


class TestConfig:
    """Tests for configuration loading."""

    def test_load_config_returns_dict(self):
        """Config loader should return a dictionary."""
        config = load_config()
        assert isinstance(config, dict)

    def test_config_has_required_sections(self):
        """Config must have sources, paths, schemas, and quality sections."""
        config = load_config()
        assert "sources" in config
        assert "paths" in config
        assert "schemas" in config
        assert "quality" in config

    def test_config_sources_structure(self):
        """Config sources must have taxi, zones, and weather."""
        config = load_config()
        sources = config["sources"]
        assert "taxi" in sources
        assert "zones" in sources
        assert "weather" in sources

    def test_config_taxi_has_months(self):
        """Taxi config must have a non-empty months list."""
        config = load_config()
        months = config["sources"]["taxi"]["months"]
        assert isinstance(months, list)
        assert len(months) > 0

    def test_config_weather_has_coordinates(self):
        """Weather config must have latitude and longitude."""
        config = load_config()
        weather = config["sources"]["weather"]
        assert "latitude" in weather
        assert "longitude" in weather
        assert isinstance(weather["latitude"], (int, float))
        assert isinstance(weather["longitude"], (int, float))


class TestDownloadFile:
    """Tests for the download_file helper."""

    @patch("src.extract.taxi_extractor.requests.get")
    def test_download_creates_file(self, mock_get):
        """download_file should create the destination file."""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "4"}
        mock_response.iter_content.return_value = [b"test"]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "test_file.txt"
            result = download_file(
                url="https://example.com/test.txt",
                dest_path=dest,
                max_retries=1,
            )
            assert result == dest
            assert dest.exists()
            assert dest.read_bytes() == b"test"

    @patch("src.extract.taxi_extractor.requests.get")
    def test_download_retries_on_failure(self, mock_get):
        """download_file should retry on HTTP errors."""
        import requests as req

        # First call fails, second succeeds
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = req.exceptions.HTTPError("500 Error")

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.headers = {"content-length": "2"}
        mock_success.iter_content.return_value = [b"ok"]
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_fail, mock_success]

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "retry_test.txt"
            result = download_file(
                url="https://example.com/test.txt",
                dest_path=dest,
                max_retries=2,
                backoff_seconds=0,  # No waiting in tests
            )
            assert dest.exists()
            assert mock_get.call_count == 2

    @patch("src.extract.taxi_extractor.requests.get")
    def test_download_raises_after_max_retries(self, mock_get):
        """download_file should raise after exhausting retries."""
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError("Failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "fail_test.txt"
            with pytest.raises(req.exceptions.ConnectionError):
                download_file(
                    url="https://example.com/test.txt",
                    dest_path=dest,
                    max_retries=2,
                    backoff_seconds=0,
                )


class TestExtractorSkipExisting:
    """Tests that extractors skip already-downloaded files (FR-4)."""

    def test_taxi_extractor_skips_existing_file(self):
        """Taxi extractor should skip files that already exist."""
        config = load_config()
        landing = Path(config["paths"]["landing_dir"])

        # Create a dummy file
        landing.mkdir(parents=True, exist_ok=True)
        month = config["sources"]["taxi"]["months"][0]
        pattern = config["sources"]["taxi"]["file_pattern"]
        filename = pattern.format(year_month=month)
        dummy = landing / filename
        dummy.write_text("dummy data")

        try:
            from src.extract.taxi_extractor import extract_taxi_data

            # This should not attempt to download since file exists
            # We patch requests.get to ensure no HTTP calls are made
            with patch("src.extract.taxi_extractor.requests.get") as mock_get:
                # Only process the first month
                test_config = config.copy()
                test_config["sources"] = config["sources"].copy()
                test_config["sources"]["taxi"] = config["sources"]["taxi"].copy()
                test_config["sources"]["taxi"]["months"] = [month]

                result = extract_taxi_data(test_config)
                assert len(result) == 1
                mock_get.assert_not_called()
        finally:
            # Cleanup
            if dummy.exists():
                dummy.unlink()
