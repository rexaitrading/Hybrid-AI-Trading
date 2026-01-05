import json
from pathlib import Path

REQ_KEYS = [
    "market_closed_today",
    "phase23_health_ok_today",
    "phase4_ok_today",
    "ev_hard_daily_ok_today",
    "gatescore_fresh_today",
    "gatescore_recent_enough",
    "gatescore_age_days",
    "nvda_blockg_ready",
    "spy_blockg_ready",
    "qqq_blockg_ready",
]

BOOL_KEYS = [
    "market_closed_today",
    "phase23_health_ok_today",
    "phase4_ok_today",
    "ev_hard_daily_ok_today",
    "gatescore_fresh_today",
    "gatescore_recent_enough",
    "nvda_blockg_ready",
    "spy_blockg_ready",
    "qqq_blockg_ready",
]

def test_blockg_status_stub_has_required_keys_and_types():
    p = Path("logs") / "blockg_status_stub.json"
    assert p.exists(), "missing logs/blockg_status_stub.json (run tools/Build-BlockGStatusStub.ps1)"
    st = json.loads(p.read_text(encoding="utf-8"))

    for k in REQ_KEYS:
        assert k in st, f"missing key: {k}"

    for k in BOOL_KEYS:
        assert isinstance(st[k], bool), f"{k} must be bool"

    assert isinstance(st["gatescore_age_days"], int), "gatescore_age_days must be int"
