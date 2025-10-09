"""
Unit Tests: settings.py (Hybrid AI Quant Pro – AAA Hedge-Fund Grade)
--------------------------------------------------------------------
Covers:
- Missing config file
- Invalid YAML (yaml.YAMLError)
- Non-dict YAML
- Generic exception when opening file
- Valid config with nested keys
- get_config_value with existing and missing keys
- load_config(force=True) refreshes CONFIG
"""

import builtins
from pathlib import Path

import hybrid_ai_trading.config.settings as settings


# ==========================================================
# Missing / Invalid Config File
# ==========================================================
def test_load_config_missing_file(monkeypatch, caplog):
    """load_config() returns {} and warns if file is missing."""
    monkeypatch.setattr(settings, "_find_config_path", lambda: "nonexistent.yaml")
    monkeypatch.setattr("os.path.exists", lambda path: False)
    with caplog.at_level("WARNING"):
        cfg = settings.load_config()
    assert cfg == {}
    assert "not found" in caplog.text.lower()


def test_load_config_non_dict_yaml(monkeypatch, tmp_path, caplog):
    """load_config() returns {} and warns if YAML is not a dict."""
    badfile: Path = tmp_path / "bad.yaml"
    badfile.write_text("justastring")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(badfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    with caplog.at_level("WARNING"):
        cfg = settings.load_config()
    assert cfg == {}
    assert "did not return a dict" in caplog.text.lower()


def test_load_config_invalid_yaml(monkeypatch, tmp_path, caplog):
    """load_config() returns {} and logs error for invalid YAML syntax."""
    badfile: Path = tmp_path / "bad.yaml"
    badfile.write_text("foo: bar: baz")  # malformed YAML
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(badfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    with caplog.at_level("ERROR"):
        cfg = settings.load_config()
    assert cfg == {}
    assert (
        "failed to parse" in caplog.text.lower() or "unexpected" in caplog.text.lower()
    )


def test_load_config_generic_exception(monkeypatch, tmp_path, caplog):
    """load_config() handles unexpected exceptions during file open."""
    goodfile: Path = tmp_path / "good.yaml"
    goodfile.write_text("foo: bar")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(goodfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Force builtins.open to raise
    monkeypatch.setattr(
        builtins,
        "open",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with caplog.at_level("ERROR"):
        cfg = settings.load_config()
    assert cfg == {}
    assert "unexpected" in caplog.text.lower()


# ==========================================================
# Valid Config
# ==========================================================
def test_load_config_valid(monkeypatch, tmp_path):
    """load_config() returns parsed dict when YAML is valid."""
    goodfile: Path = tmp_path / "good.yaml"
    goodfile.write_text("features:\n  enable: true\n  nested:\n    key: 123")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(goodfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    cfg = settings.load_config()
    assert cfg["features"]["enable"] is True
    assert cfg["features"]["nested"]["key"] == 123


# ==========================================================
# get_config_value
# ==========================================================
def test_get_config_value_existing_and_missing(monkeypatch):
    """get_config_value returns correct values and defaults."""
    fake_cfg = {"a": {"b": {"c": 123}}}
    monkeypatch.setattr(settings, "CONFIG", fake_cfg)
    assert settings.get_config_value("a", "b", "c") == 123
    assert settings.get_config_value("a", "x", default="missing") == "missing"
    assert settings.get_config_value("invalid", default="Y") == "Y"


# ==========================================================
# Force Reload
# ==========================================================
def test_force_reload(monkeypatch, tmp_path):
    """load_config(force=True) refreshes the global CONFIG object."""
    newfile: Path = tmp_path / "new.yaml"
    newfile.write_text("foo: bar")
    monkeypatch.setattr(settings, "_find_config_path", lambda: str(newfile))
    monkeypatch.setattr("os.path.exists", lambda path: True)
    settings.load_config(force=True)
    assert settings.CONFIG == {"foo": "bar"}
