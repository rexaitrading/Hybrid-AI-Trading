from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.phase7.preflight_gate import ensure_phase7_ready


def _write(p: Path, obj: dict) -> None:
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def test_phase7_preflight_passes(monkeypatch, tmp_path: Path):
    fp = tmp_path / "phase6_daily_summary.json"
    _write(fp, {
        "as_of_date": "2025-12-27",
        "readiness": {
            "blockg": {"nvda_blockg_ready": True, "spy_blockg_ready": True, "qqq_blockg_ready": True},
            "portfolio_halt": {"ok": True, "reason": "portfolio_halt_ok", "cfg": {}},
        },
        "gatescore_by_symbol": {"NVDA": {}, "SPY": {}, "QQQ": {}},
    })
    monkeypatch.setenv("HAT_PHASE6_DAILY_SUMMARY_PATH", str(fp))
    ensure_phase7_ready(required_symbols=("NVDA","SPY","QQQ"), as_of_date="2025-12-27")


def test_phase7_preflight_blocks_when_nvda_not_ready(monkeypatch, tmp_path: Path):
    fp = tmp_path / "phase6_daily_summary.json"
    _write(fp, {
        "as_of_date": "2025-12-27",
        "readiness": {
            "blockg": {"nvda_blockg_ready": False},
            "portfolio_halt": {"ok": True, "reason": "ok", "cfg": {}},
        },
        "gatescore_by_symbol": {"NVDA": {}},
    })
    monkeypatch.setenv("HAT_PHASE6_DAILY_SUMMARY_PATH", str(fp))
    with pytest.raises(RuntimeError) as e:
        ensure_phase7_ready(required_symbols=("NVDA",), as_of_date="2025-12-27")
    assert "PHASE7_PREFLIGHT_DENY" in str(e.value)


def test_phase7_preflight_blocks_when_portfolio_halt_not_ok(monkeypatch, tmp_path: Path):
    fp = tmp_path / "phase6_daily_summary.json"
    _write(fp, {
        "as_of_date": "2025-12-27",
        "readiness": {
            "blockg": {"nvda_blockg_ready": True},
            "portfolio_halt": {"ok": False, "reason": "portfolio_halt_metrics_missing", "cfg": {}},
        },
        "gatescore_by_symbol": {"NVDA": {}},
    })
    monkeypatch.setenv("HAT_PHASE6_DAILY_SUMMARY_PATH", str(fp))
    with pytest.raises(RuntimeError):
        ensure_phase7_ready(required_symbols=("NVDA",), as_of_date="2025-12-27")


def test_phase7_preflight_blocks_when_gatescore_missing_symbol(monkeypatch, tmp_path: Path):
    fp = tmp_path / "phase6_daily_summary.json"
    _write(fp, {
        "as_of_date": "2025-12-27",
        "readiness": {
            "blockg": {"nvda_blockg_ready": True},
            "portfolio_halt": {"ok": True, "reason": "ok", "cfg": {}},
        },
        "gatescore_by_symbol": {"SPY": {}},
    })
    monkeypatch.setenv("HAT_PHASE6_DAILY_SUMMARY_PATH", str(fp))
    with pytest.raises(RuntimeError):
        ensure_phase7_ready(required_symbols=("NVDA",), as_of_date="2025-12-27")
