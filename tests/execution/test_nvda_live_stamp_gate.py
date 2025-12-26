from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.live_ready_stamp import LiveStampNotReady, require_nvda_live_stamp


def test_nvda_live_stamp_blocks_when_disarmed(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    # Write a DISARMED stamp for today (no-BOM not required; loader is utf-8-sig tolerant)
    stamp = {
        "ts_utc": "2025-01-01T00:00:00Z",
        "as_of_date": "9999-12-31",  # intentionally wrong date so it blocks
        "nvda_live_ready": False,
        "reason": "manual_disarm",
    }
    p = tmp_path / "nvda_live_ready_stamp.json"
    p.write_text(json.dumps(stamp), encoding="utf-8")

    monkeypatch.setenv("HAT_LIVE_READY_STAMP_PATH", str(p))

    with pytest.raises(LiveStampNotReady):
        require_nvda_live_stamp("NVDA")

    # Non-NVDA symbols should not be gated by the NVDA stamp
    require_nvda_live_stamp("SPY")
