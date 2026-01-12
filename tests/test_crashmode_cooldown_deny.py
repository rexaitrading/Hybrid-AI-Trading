import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint


class DummyIB:
    def __init__(self):
        self.calls = []

    # Accept both call styles used by ib_safe.py
    def placeOrder(self, *args):
        self.calls.append(args)
        return {"ok": True, "args": args}


class DummyContract:
    def __init__(self, symbol="NVDA"):
        self.symbol = symbol


class DummyOrder:
    pass


class DummyCtx:
    # Minimal RunContext-like object
    def __init__(self, repo_root: str, mode: str):
        self.repo_root = repo_root
        self.mode = mode
        # is_paper must exist; LIVE/PAPERLIVE are not paper
        self.is_paper = False
        self.market = "US"


def _write_cooldown(repo_root: Path, minutes_ahead: int) -> None:
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    until = now + timedelta(minutes=minutes_ahead)
    payload = {
        "ts_utc": now.isoformat().replace("+00:00", "Z"),
        "symbol": "NVDA",
        "crisis_regime": True,
        "cooldown_minutes": minutes_ahead,
        "cooldown_until_utc": until.isoformat().replace("+00:00", "Z"),
    }
    (logs / "crisis_cooldown.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.mark.parametrize("mode", ["LIVE", "PAPERLIVE"])
def test_crashmode_cooldown_denies_new_orders(tmp_path: Path, mode: str) -> None:
    _write_cooldown(tmp_path, minutes_ahead=60)

    ib = DummyIB()
    ctx = DummyCtx(repo_root=str(tmp_path), mode=mode)
    c = DummyContract("NVDA")
    o = DummyOrder()

    with pytest.raises(RuntimeError) as e:
        ib_place_order_chokepoint(ib, c, o, ctx=ctx, meta={"symbol": "NVDA"})
    assert "CRASHMODE_DENY" in str(e.value)
    assert len(ib.calls) == 0


@pytest.mark.parametrize("mode", ["LIVE", "PAPERLIVE"])
def test_crashmode_allows_risk_action_bypass_flag(tmp_path: Path, mode: str) -> None:
    _write_cooldown(tmp_path, minutes_ahead=60)

    ib = DummyIB()
    ctx = DummyCtx(repo_root=str(tmp_path), mode=mode)
    c = DummyContract("NVDA")
    o = DummyOrder()

    # allow_risk_action=True should bypass cooldown deny so flatten tools can place orders
    res = ib_place_order_chokepoint(ib, c, o, ctx=ctx, meta={"symbol": "NVDA", "allow_risk_action": True})
    assert res["ok"] is True
    assert len(ib.calls) == 1
