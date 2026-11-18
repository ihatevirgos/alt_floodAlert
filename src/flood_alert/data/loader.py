"""Loads thresholds, transition table, outputs and scenario presets from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = ROOT / "config"
SCENARIO_DIR = ROOT / "scenarios"


def _read(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_config(config_dir: str | Path | None = None) -> Dict[str, dict]:
    d = Path(config_dir) if config_dir else CONFIG_DIR
    return {
        "thresholds": _read(d / "thresholds.json"),
        "transitions": _read(d / "transitions.json"),
        "outputs": _read(d / "outputs.json"),
    }


def list_scenarios(scenario_dir: str | Path | None = None) -> List[Path]:
    d = Path(scenario_dir) if scenario_dir else SCENARIO_DIR
    return sorted(d.glob("*.json"))


def load_scenario(path: str | Path) -> dict:
    data = _read(Path(path))
    for e in data["events"]:
        if not (isinstance(e, (int, float)) or (isinstance(e, str) and e.upper() == "T")):
            raise ValueError(f"{path}: events must be numbers or \"T\", got {e!r}")
    return data
