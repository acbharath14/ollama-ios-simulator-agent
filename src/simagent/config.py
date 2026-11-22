"""JSON config file for defaults. CLI flags override config values."""

import json
import os

DEFAULTS = {
    "ollama_host": "http://127.0.0.1:11434",
    "vision_model": "qwen2.5vl:7b",
    "coder_model": "qwen2.5-coder:7b",
    "device_name": "iPhone 16 Pro",
    "tap_scale": 2,
    "scheme": None,
    "project": None,
    "workspace": None,
    "screenshots_dir": "screenshots",
    "reports_dir": "reports",
}

CONFIG_FILENAME = "simagent.json"


def load_config(path):
    """Load a JSON config file. Missing file means empty config."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object: %s" % path)
    return data


def find_config(explicit_path=None):
    """Explicit path wins; otherwise ./simagent.json when it exists."""
    if explicit_path:
        return explicit_path
    if os.path.exists(CONFIG_FILENAME):
        return CONFIG_FILENAME
    return None


def resolve(config=None, **overrides):
    """Defaults, then config file, then CLI overrides. None never overrides."""
    merged = dict(DEFAULTS)
    merged.update(config or {})
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged
