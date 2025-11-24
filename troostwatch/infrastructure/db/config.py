from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_DB_TIMEOUT = 30.0

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_FILE = _REPO_ROOT / "config.json"


def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load ``config.json`` if present and return it as a dictionary."""

    path = Path(config_path) if config_path is not None else _CONFIG_FILE
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return the loaded project configuration as a dictionary."""

    return load_config(config_path)


def get_path_config(config_path: Path | str | None = None) -> Dict[str, Path]:
    """Return resolved filesystem paths from the project configuration."""

    cfg = load_config(config_path)
    root = Path(config_path).parent if config_path is not None else _CONFIG_FILE.parent
    defaults = {
        "db_path": root / "troostwatch.db",
        "snapshots_root": root / "snapshots",
        "lot_cards_dir": root / "snapshots" / "lot_cards",
        "lot_details_dir": root / "snapshots" / "lot_details",
    }
    paths_cfg = cfg.get("paths", {}) if isinstance(cfg.get("paths", {}), dict) else {}
    resolved: Dict[str, Path] = {}
    for key, default_value in defaults.items():
        raw_value = paths_cfg.get(key, default_value)
        resolved_value = Path(raw_value)
        if not resolved_value.is_absolute():
            resolved_value = (root / resolved_value).resolve()
        resolved[key] = resolved_value
    return resolved


def get_default_timeout(config_path: Path | str | None = None) -> float:
    """Read the preferred database timeout from configuration."""

    cfg = load_config(config_path)
    try:
        return float(cfg.get("db_timeout_seconds", DEFAULT_DB_TIMEOUT))
    except (TypeError, ValueError):
        return DEFAULT_DB_TIMEOUT
