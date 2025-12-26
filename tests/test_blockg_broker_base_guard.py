from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.brokers.base import _blockg_guard_live
from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
from hybrid_ai_trading.runtime.run_context import RunContext


def test_blockg_guard_blocks_live_when_not_ready(tmp_path: Path, monkeypatch):
    status = {
        "nvda_blockg_ready": False,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        "reasons_not_ready": ["nvda_blockg_ready=false"],
    }
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps(status), encoding="utf-8")

    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    ctx = RunContext.from_env_and_args(symbol="NVDA", regime="test", mode="live")

    with pytest.raises(BlockGNotReady):
        _blockg_guard_live("NVDA", ctx=ctx)
