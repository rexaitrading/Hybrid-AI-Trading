from __future__ import annotations

import json
from pathlib import Path

from hybrid_ai_trading.portfolio.logging import append_fill


def test_phase6_append_fill_creates_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"ts_utc": "2025-12-17T00:00:00Z", "symbol": "NVDA", "qty": 1, "price": 100.0}
    append_fill(payload=payload)

    p = tmp_path / "logs" / "portfolio_fills.jsonl"
    assert p.exists()

    line = p.read_text(encoding="utf-8").splitlines()[0]
    obj = json.loads(line)
    assert obj["symbol"] == "NVDA"