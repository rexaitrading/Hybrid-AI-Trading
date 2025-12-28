from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.execution.blockg_contract import read_blockg_status


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_readiness_snapshot(*, portfolio_metrics: Dict[str, Any] | None = None) -> Dict[str, Any]:
    st = read_blockg_status()
    return {
        "blockg_status": dict(st),
        "portfolio_metrics": dict(portfolio_metrics or {}),
    }


def write_readiness_snapshot(path: Path | None = None, *, portfolio_metrics: Dict[str, Any] | None = None) -> Path:
    outp = path or (_repo_root() / "logs" / "phase6_readiness_snapshot.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    snap = build_readiness_snapshot(portfolio_metrics=portfolio_metrics)
    outp.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return outp
