from __future__ import annotations

from pathlib import Path
import os
import json
from datetime import datetime, timezone
from datetime import timedelta
import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint
def _write_live_arm_token(symbol: str, tmp_path: Path) -> None:
    # live_arm.py stores tokens at <repo_root>/logs/live_arm_<sym>.json
    # Tests override via HAT_LIVE_ARM_TOKEN_PATH to keep temp isolated.
    from hybrid_ai_trading.execution.live_arm import _token_path
    token_path = tmp_path / f"live_arm_{symbol.lower()}.json"
    os.environ["HAT_LIVE_ARM_TOKEN_PATH"] = str(token_path)
    p = _token_path(symbol)
    p.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    exp = (now + timedelta(minutes=30)).isoformat().replace('+00:00','Z')
    today = now.strftime('%Y-%m-%d')
    p.write_text(json.dumps({'symbol':symbol,'as_of_date':today,'expires_utc':exp}), encoding='utf-8')
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
    _write_live_arm_token('NVDA', tmp_path)

    # Make Block-G always fail
    def _fail(sym: str, *a, **k):
        raise RuntimeError("BLOCKG_NOT_READY_TEST")
    monkeypatch.setattr("hybrid_ai_trading.broker.ib_safe.require_blockg_ready_for_live", _fail)

    ib = _IB()
    with pytest.raises(RuntimeError, match="BLOCKG_NOT_READY_TEST"):
        ib_place_order_chokepoint(ib, _C("NVDA"), object())

    assert ib.called is False



