from __future__ import annotations

import json
from pathlib import Path

from hybrid_ai_trading.cost_model import CostInputs, estimate_cost


def _safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> None:
    root = Path(r"C:\Users\rhcy9\OneDrive\文件\HybridAITrading")
    jsonl_path = root / "research" / "nvda_bplus_replay_trades.jsonl"

    print("[COST] Using JSONL:", jsonl_path)

    trades = []
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    print("[COST] [WARN] Skipping invalid JSON line")
                    continue
                trades.append(obj)
    except FileNotFoundError:
        print("[COST] ERROR: JSONL file not found.")
        return

    if not trades:
        print("[COST] No trades loaded from JSONL.")
        return

    print(f"[COST] Loaded {len(trades)} trades. Showing cost breakdown per trade:")

    for t in trades:
        tag = t.get("bar_replay_tag") or t.get("tag") or "UNKNOWN_TAG"

        # infer entry price and quantity from common fields
        entry_px = (
            _safe_float(t.get("entry_px"), None)
            or _safe_float(t.get("entry_price"), None)
            or _safe_float(t.get("fill_px"), None)
            or _safe_float(t.get("fill_price"), None)
        )
        qty = (
            _safe_float(t.get("qty"), None)
            or _safe_float(t.get("quantity"), None)
            or _safe_float(t.get("shares"), None)
        )

        if not entry_px or not qty:
            print(f"[COST] WARN tag={tag}: missing entry_px/qty, skipping cost calc.")
            continue

        side = (t.get("side") or t.get("direction") or "BUY").upper()

        ci = CostInputs(
            symbol="NVDA",
            side=side,
            mid_price=entry_px,
            qty=qty,
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
            f"[COST] tag={tag} side={side} notional={notional:.2f} "
            f"total_cost={cost:.4f} cost_bp={cost_bp:.2f} "
            f"(spread={cb.spread_cost:.4f}, slip={cb.slippage_cost:.4f}, fee={cb.fee_cost:.4f})"
        )


if __name__ == "__main__":
    main()