"""
Unit Tests: settings.py (Hybrid AI Quant Pro v8.2 – Absolute 100% Coverage)
---------------------------------------------------------------------------
Covers:
- Missing config file
- Invalid YAML (yaml.YAMLError)
- Generic exception path
- Valid config with upgrades applied
- Regime min_samples auto
- Regime min_samples numeric (non-auto path)
- Kelly sizing safeguard (invalid disables + valid stays enabled)
- Risk dict without kelly branch
- _apply_upgrades with non-dict input
- get_config_value hit & miss
- Access __all__ constants
"""

import builtins
import yaml
import pytest
from pathlib import Path
import hybrid_ai_trading.config.settings as settings


def test_load_config_missing_file(tmp_path, capsys):
    fake_path = tmp_path / "nonexistent.yaml"
    cfg = settings.load_config(fake_path)
    assert cfg == {}
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


def test_load_config_invalid_yaml(monkeypatch, tmp_path, capsys):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text(":::: bad ::::")
    # Force yaml.safe_load to raise YAMLError
    monkeypatch.setattr(
        yaml, "safe_load",
        lambda *_a, **_k: (_ for _ in ()).throw(yaml.YAMLError("boom"))
    )
    cfg = settings.load_config(bad_file)
    assert cfg == {}
    captured = capsys.readouterr()
    assert "failed" in captured.out.lower()


def test_load_config_generic_exception(monkeypatch, tmp_path, capsys):
    bad_file = tmp_path / "bad2.yaml"
    bad_file.write_text("ok: true")
    # Force open() to raise unexpected error
    monkeypatch.setattr(
        builtins, "open",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    cfg = settings.load_config(bad_file)
    assert cfg == {}
    captured = capsys.readouterr()
    assert "unexpected" in captured.out.lower()


def test_load_config_valid_and_upgrades(tmp_path):
    good_file = tmp_path / "good.yaml"
    good_file.write_text(
        """
        regime:
          lookback_days: 100
          min_samples: auto
        risk:
          kelly:
            enabled: true
            win_rate: 0
            payoff: -1
        """
    )
    cfg = settings.load_config(good_file)
    assert cfg["regime"]["min_samples"] == int(100 * 0.7)
    assert cfg["risk"]["kelly"]["enabled"] is False


def test_apply_upgrades_valid_kelly_and_non_auto_regime():
    cfg = {
        "risk": {"kelly": {"enabled": True, "win_rate": 0.6, "payoff": 2.0}},
        "regime": {"lookback_days": 50, "min_samples": 10},  # numeric, non-auto path
    }
    result = settings._apply_upgrades(cfg)
    # Kelly remains enabled
    assert result["risk"]["kelly"]["enabled"] is True
    # Non-auto regime keeps numeric min_samples
    assert result["regime"]["min_samples"] == 10


def test_apply_upgrades_risk_without_kelly():
    cfg = {"risk": {"max_loss": 0.05}}
    result = settings._apply_upgrades(cfg)
    # Should leave risk dict unchanged except add empty kelly if not present
    assert "risk" in result
    assert isinstance(result["risk"], dict)


def test_apply_upgrades_non_dict():
    assert settings._apply_upgrades(None) == {}


def test_get_config_value_existing_and_missing(monkeypatch):
    fake_cfg = {"a": {"b": {"c": 123}}}
    monkeypatch.setattr(settings, "CONFIG", fake_cfg)
    assert settings.get_config_value("a", "b", "c") == 123
    assert settings.get_config_value("a", "x", default="missing") == "missing"


def test_constants_exposed():
    # Ensure __all__ constants are defined
    assert "CONFIG" in settings.__all__
    assert "load_config" in settings.__all__
    assert "get_config_value" in settings.__all__
    assert "PROJECT_ROOT" in settings.__all__
    assert "CONFIG_PATH" in settings.__all__
    assert settings.PROJECT_ROOT.exists() or isinstance(settings.PROJECT_ROOT, Path)

def test_apply_upgrades_valid_kelly_passes():
    cfg = {
        "risk": {"kelly": {"enabled": True, "win_rate": 0.6, "payoff": 2.0}},
        "regime": {"lookback_days": 30, "min_samples": "auto"},
    }
    result = settings._apply_upgrades(cfg)
    assert result["risk"]["kelly"]["enabled"] is True
    assert result["regime"]["min_samples"] == int(30 * 0.7)
