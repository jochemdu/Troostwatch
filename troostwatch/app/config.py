"""Configuration utilities for Troostwatch.

Provides helper functions for loading and parsing configuration from JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A dictionary of configuration values.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


__all__ = ["load_config"]
