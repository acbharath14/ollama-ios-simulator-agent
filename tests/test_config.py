import json

import pytest

from simagent import config


def test_resolve_defaults():
    cfg = config.resolve()
    assert cfg["ollama_host"] == "http://127.0.0.1:11434"
    assert cfg["vision_model"] == "qwen2.5vl:7b"
    assert cfg["coder_model"] == "qwen2.5-coder:7b"
    assert cfg["device_name"] == "iPhone 16 Pro"
    assert cfg["tap_scale"] == 2


def test_resolve_config_then_overrides():
    cfg = config.resolve(
        {"device_name": "iPhone SE", "tap_scale": 1},
        device_name="iPhone 17",
        tap_scale=None,
    )
    assert cfg["device_name"] == "iPhone 17"
    assert cfg["tap_scale"] == 1


def test_resolve_none_never_overrides():
    cfg = config.resolve({"device_name": "iPhone SE"}, device_name=None)
    assert cfg["device_name"] == "iPhone SE"


def test_load_config_missing_file(tmp_path):
    assert config.load_config(str(tmp_path / "nope.json")) == {}
    assert config.load_config(None) == {}


def test_load_config_round_trip(tmp_path):
    path = tmp_path / "simagent.json"
    path.write_text(json.dumps({"device_name": "iPhone SE"}), encoding="utf-8")
    assert config.load_config(str(path)) == {"device_name": "iPhone SE"}


def test_load_config_bad_json(tmp_path):
    path = tmp_path / "simagent.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        config.load_config(str(path))


def test_load_config_not_an_object(tmp_path):
    path = tmp_path / "simagent.json"
    path.write_text('["a", "b"]', encoding="utf-8")
    with pytest.raises(ValueError):
        config.load_config(str(path))
