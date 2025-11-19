from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.cost_model import CostInputs, estimate_cost


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe cost model on replay trades JSONL."
    )
    parser.add_argument(
        "--jsonl",
        required=True,
        help="Path to replay trades JSONL file.",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    print("[COST-GEN] Using JSONL:", jsonl_path)

    if not jsonl_path.exists():
        print("[COST-GEN] ERROR: JSONL file not found.")
        return

    trades = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[COST-GEN] WARN: Skipping invalid JSON line.")
                continue
            trades.append(obj)

    if not trades:
        print("[COST-GEN] No trades loaded from JSONL.")
        return

    print(f"[COST-GEN] Loaded {len(trades)} trades. Cost breakdown:")

    for t in trades:
        tag = t.get("bar_replay_tag") or t.get("tag") or "UNKNOWN_TAG"
        symbol = str(t.get("symbol") or "UNKNOWN")
        side = (str(t.get("side") or t.get("direction") or "BUY")).upper()

        entry_px = t.get("entry_px") or t.get("entry_price") or t.get("fill_px") or t.get("fill_price")
        qty = t.get("qty") or t.get("quantity") or t.get("shares")

        mid_price = _safe_float(entry_px, 0.0)
        qty_f = _safe_float(qty, 0.0)

        if mid_price <= 0.0 or qty_f <= 0.0:
            print(f"[COST-GEN] WARN tag={tag} symbol={symbol}: missing entry_px/qty, skipping cost calc.")
            continue

        ci = CostInputs(
            symbol=symbol,
            side=side,
            mid_price=mid_price,
            qty=qty_f,
            spread=None,
            fee_per_share=None,
            fee_rate_bp=None,
            expected_slippage_bp=None,
        )
        cb = estimate_cost(ci)

        notional = cb.notional
        cost = cb.total_cost
        cost_bp = (cost / notional * 1e4) if notional else 0.0

        print(
            f"[COST-GEN] tag={tag} symbol={symbol} side={side} notional={notional:.2f} "
            f"total_cost={cost:.4f} cost_bp={cost_bp:.2f} "
            f"(spread={cb.spread_cost:.4f}, slip={cb.slippage_cost:.4f}, fee={cb.fee_cost:.4f})"
        )


if __name__ == "__main__":
    main()