"""Data layer: JSON configuration and scenario presets."""

from .loader import CONFIG_DIR, SCENARIO_DIR, list_scenarios, load_config, load_scenario

__all__ = ["CONFIG_DIR", "SCENARIO_DIR", "list_scenarios", "load_config", "load_scenario"]
