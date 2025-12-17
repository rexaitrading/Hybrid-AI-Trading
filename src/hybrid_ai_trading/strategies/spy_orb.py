from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _load_candidates(symbol: str, limit: int | None = 50) -> List[Dict[str, Any]]:
    src = Path("logs") / "paper_trades.jsonl"
    if not src.exists():
        return []

    sym = symbol.upper()
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
            if str(row.get("symbol", "")).upper() != sym:
                continue
            ts = row.get("ts")
            if not ts:
                continue

            signal = str(row.get("signal") or "").upper()
            side = "SELL" if signal.startswith("SHORT") else "BUY"
            qty = row.get("qty", 1.0)
            price = row.get("price", 0.0)

            out.append(
                {
                    "symbol": sym,
                    "side": side,
                    "qty": float(qty or 0.0),
                    "price": float(price or 0.0),
                    # PAPER boundary (safe): no LIVE tag
                    "regime": "SPY_ORB_PAPER",
                    "day_id": "PAPER",
                    "entry_ts": ts,
                    "edge_ratio": row.get("edge_ratio"),
                    "micro_score": row.get("micro_score"),
                }
            )

            if limit is not None and len(out) >= int(limit):
                break
    return out


def signal_fn(_market_state: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True}


def order_plan_fn(_signal: Dict[str, Any], _ctx: object, _portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _load_candidates("SPY", limit=50)