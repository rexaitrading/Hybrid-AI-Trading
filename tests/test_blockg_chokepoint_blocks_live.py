from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone
import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint

def _write_nvda_stamp_ready(tmp_path: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = tmp_path / "nvda_live_ready_stamp.json"
    p.write_text(json.dumps({"ts_utc":"2025-01-01T00:00:00Z","as_of_date":today,"nvda_live_ready":True}) + "\n", encoding="utf-8")
    return p


class _C:
    def __init__(self, symbol: str):
        self.symbol = symbol

class _IB:
    def __init__(self):
        self.called = False
    def placeOrder(self, *a, **k):
        self.called = True
        return None

def test_chokepoint_blocks_live_when_not_ready(tmp_path, monkeypatch):
    # Force "live"
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    stamp = _write_nvda_stamp_ready(tmp_path)
    monkeypatch.setenv("HAT_LIVE_READY_STAMP_PATH", str(stamp))

    # Make Block-G always fail
    def _fail(sym: str, *a, **k):
        raise RuntimeError("BLOCKG_NOT_READY_TEST")
    monkeypatch.setattr("hybrid_ai_trading.broker.ib_safe.ensure_symbol_blockg_ready", _fail)

    ib = _IB()
    with pytest.raises(RuntimeError, match="BLOCKG_NOT_READY_TEST"):
        ib_place_order_chokepoint(ib, _C("NVDA"), object())

    assert ib.called is False
