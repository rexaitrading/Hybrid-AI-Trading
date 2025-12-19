from __future__ import annotations

import json
from pathlib import Path
import os

def _paper_trades_path() -> Path:
    # Optional override so ops can feed merged temp JSONL without contaminating logs/paper_trades.jsonl
    p = (os.getenv("HAT_PAPER_TRADES_PATH", "") or "").strip()
    if p:
        return Path(p)
    return Path("logs") / "paper_trades.jsonl"
from typing import Any, Dict, List


def _load_nvda_paper_candidates(limit: int | None = 50) -> List[Dict[str, Any]]:
    """
    Read NVDA rows from logs/paper_trades.jsonl and convert into simple intent dicts.
    PAPER-first: this is used only to exercise the Phase-6 router path safely.
    """
    src = _paper_trades_path()
    if not src.exists():
        return []

    out: List[Dict[str, Any]] = []
    with src.open("r", encoding="utf-8-sig") as f:
        for line in f:
            ln = line.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue
            if str(row.get("symbol", "")).upper() != "NVDA":
                continue
            ts = row.get("ts")
            if not ts:
                continue

            signal = str(row.get("signal") or "").upper()
            if signal.startswith("SHORT"):
                side = "SELL"
            else:
                side = "BUY"

            qty = row.get("qty", 1.0)
            price = row.get("price", 0.0)

            out.append(
                {
                    "symbol": "NVDA",
                    "side": side,
                    "qty": float(qty or 0.0),
                    "price": float(price or 0.0),
                    # PAPER boundary: DO NOT include LIVE in regime here
                    "regime": "NVDA_BPLUS_PAPER",
                    "day_id": "PAPER",
                    "entry_ts": ts,
                    # Optional: pass through gatescore fields if present
                    "edge_ratio": row.get("edge_ratio"),
                    "micro_score": row.get("micro_score"),
                }
            )

            if limit is not None and len(out) >= int(limit):
                break

    return out


def signal_fn(_market_state: Dict[str, Any]) -> Dict[str, Any]:
    # Phase-6 scaffold: signals are pre-generated from paper_trades.jsonl
    return {"ok": True}


def order_plan_fn(_signal: Dict[str, Any], _ctx: object, _portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _load_nvda_paper_candidates(limit=50)