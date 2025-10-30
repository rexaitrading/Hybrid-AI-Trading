"""
Unit Tests: settings.py (Hybrid AI Quant Pro – 100% Coverage)
-------------------------------------------------------------
Covers:
- Missing config file
- Config returns non-dict
- YAML parsing error
- File open exception (new → covers lines 45–47)
- Valid config dictionary
- get_config_value with nested keys and defaults
- load_config(force=True) refreshes global CONFIG
"""

import hybrid_ai_trading.config.settings as settings


def test_missing_file(monkeypatch, caplog):
    monkeypatch.setattr(settings, "_find_config_path", lambda: "nonexistent.yaml")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    with caplog.at_level("WARNING"):
        cfg = settings.load_config()
    assert cfg == {}
    assert "Config file not found" in caplog.text


def test_non_dict_yaml(monkeypatch, tmp_path, caplog):
    badfile = tmp_path / "bad.yaml"
    badfile.write_text("justastring")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(badfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    with caplog.at_level("WARNING"):
        cfg = settings.load_config()
    assert cfg == {}
    assert "did not return a dict" in caplog.text


def test_yaml_parse_error(monkeypatch, tmp_path, caplog):
    badfile = tmp_path / "bad.yaml"
    badfile.write_text("foo: bar: baz")  # invalid YAML
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(badfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    with caplog.at_level("ERROR"):
        cfg = settings.load_config()
    assert cfg == {}
    assert (
        "Failed to parse YAML" in caplog.text or "Failed to load/parse" in caplog.text
    )


def test_file_open_exception(monkeypatch, caplog):
    """Covers the bare except branch (lines 45–47)."""
    monkeypatch.setattr(settings, "_find_config_path", lambda: "bad.yaml")
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr(
        "builtins.open", lambda *a, **k: (_ for _ in ()).throw(OSError("boom"))
    )
    with caplog.at_level("ERROR"):
        cfg = settings.load_config()
    assert cfg == {}
    # ✅ Match the actual log message from settings.py
    assert "Unexpected error reading config.yaml" in caplog.text


def test_valid_config(monkeypatch, tmp_path):
    goodfile = tmp_path / "good.yaml"
    goodfile.write_text("features:\n  enable: true\n  nested:\n    key: 123")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(goodfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    cfg = settings.load_config()
    assert cfg["features"]["enable"] is True
    assert cfg["features"]["nested"]["key"] == 123


def test_get_config_value(monkeypatch):
    fake_config = {"level1": {"level2": {"value": 42}}}
    monkeypatch.setattr(settings, "CONFIG", fake_config)
    assert settings.get_config_value("level1", "level2", "value") == 42
    assert settings.get_config_value("level1", "missing", default="X") == "X"
    assert settings.get_config_value("invalid", default="Y") == "Y"


def test_force_reload(monkeypatch, tmp_path):
    newfile = tmp_path / "new.yaml"
    newfile.write_text("foo: bar")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(newfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    settings.load_config(force=True)
    assert settings.CONFIG == {"foo": "bar"}
