# PYTEST_IMPORT_SHIM: ensure repo src/ is importable regardless of CWD/interpreter
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
s = str(SRC)
if s not in sys.path:
    sys.path.insert(0, s)

import types

import hybrid_ai_trading.runners.paper_quantcore as qc
from hybrid_ai_trading.runners.paper_trader import _qc_run_once


def test_qc_adapter_legacy_with_snapshots(monkeypatch):
    def legacy(cfg, logger, snapshots=None):
        # legacy returns a LIST
        return [{"symbol": "AAPL", "decision": {}}]

    monkeypatch.setattr(qc, "run_once", legacy, raising=True)
    out = _qc_run_once(["AAPL"], [{"symbol": "AAPL", "price": 123.0}], {"x": 1}, None)
    assert isinstance(out, dict)
    assert "items" in out and isinstance(out["items"], list) and out["items"]
    assert out["summary"]["decisions"] == len(out["items"])


def test_qc_adapter_legacy_plain(monkeypatch):
    def legacy_plain(cfg, logger):
        # legacy returns a DICT
        return {
            "summary": {"rows": 1, "batches": 1, "decisions": 1},
            "items": [{"symbol": "AAPL", "decision": {}}],
        }

    monkeypatch.setattr(qc, "run_once", legacy_plain, raising=True)
    out = _qc_run_once(["AAPL"], [{"symbol": "AAPL", "price": 123.0}], {"x": 1}, None)
    assert isinstance(out, dict) and "items" in out
    assert out["summary"]["decisions"] == 1


def test_qc_adapter_newstyle(monkeypatch):
    def newstyle(symbols, price_map, risk_mgr):
        # new-style returns a LIST
        return [{"symbol": s, "decision": {}} for s in symbols]

    monkeypatch.setattr(qc, "run_once", newstyle, raising=True)
    out = _qc_run_once(
        ["AAPL", "MSFT"],
        [{"symbol": "AAPL", "price": 1}, {"symbol": "MSFT", "price": 2}],
        {"x": 1},
        None,
    )
    assert isinstance(out, dict) and "items" in out
    assert len(out["items"]) == 2
