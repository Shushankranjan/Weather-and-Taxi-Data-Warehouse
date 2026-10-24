"""
Configuration loader.

Reads config/config.yaml and provides a single dict for all modules.
"""

import yaml
from pathlib import Path


def load_config(config_path: str = None) -> dict:
    """
    Load the YAML configuration file.

    Args:
        config_path: Optional path to config file.
                     Defaults to config/config.yaml relative to project root.

    Returns:
        Configuration dictionary.
    """
    if config_path is None:
        root = Path(__file__).resolve().parent.parent.parent
        config_path = root / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
