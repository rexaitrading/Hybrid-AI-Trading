from __future__ import annotations

import json
import os
from typing import List

from hybrid_ai_trading.risk_manager_phase5_bridge import (
    PositionSnapshot,
    AddRequest,
    RiskManagerPhase5,
)


def load_aapl_trades(jsonl_path: str, limit: int = 5) -> List[dict]:
    trades: List[dict] = []
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"AAPL enriched JSONL not found: {jsonl_path}")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            trades.append(rec)
            if len(trades) >= limit:
                break
    return trades


def main() -> None:
    jsonl_path = os.getenv(
        "HAT_AAPL_ENRICHED_JSONL",
        os.path.join("research", "aapl_orb_vwap_replay_trades_enriched.jsonl"),
    )
    trades = load_aapl_trades(jsonl_path=jsonl_path, limit=5)

    rm = RiskManagerPhase5()

    print("[MockTradeEngine] Using RiskConfig:", rm.risk_cfg)
    print("[MockTradeEngine] Using CostConfig:", rm.cost_cfg)
    print("[MockTradeEngine] Loaded", len(trades), "AAPL ORB/VWAP trades from", jsonl_path)

    # Start with no position, then grow notional as if we are adding size each trade
    current_notional = 0.0

    for idx, t in enumerate(trades, start=1):
        symbol = t.get("symbol", "AAPL")
        side = "LONG"  # ORB/VWAP BUY for now
        pnl_pct = float(t.get("pnl_pct", 0.0))
        # Convert pnl_pct to bp for the gate (unrealized; here we treat it as current per-trade PnL)
        unrealized_pnl_bp = pnl_pct * 10_000.0

        # Hypothetical notional sizes
        base_notional = float(t.get("cost_notional") or 10_000.0)
        if current_notional == 0.0:
            current_notional = base_notional
        additional_notional = base_notional  # attempt to double size
        additional_shares_round_trip = 100

        pos = PositionSnapshot(
            symbol=symbol,
            side=side,
            unrealized_pnl_bp=unrealized_pnl_bp,
            notional=current_notional,
        )
        add_req = AddRequest(
            additional_notional=additional_notional,
            additional_shares_round_trip=additional_shares_round_trip,
        )

        can_add = rm.can_add(pos, add_req)

        print(
            f"[MockTradeEngine] trade #{idx} "
            f"symbol={symbol} "
            f"pnl_pct={pnl_pct:.4f} "
            f"unrealized_pnl_bp={unrealized_pnl_bp:.2f} "
            f"notional={current_notional:.0f} "
            f"add_notional={additional_notional:.0f} "
            f"-> can_add={can_add}"
        )

        # If allowed, we 'scale in' by increasing notional
        if can_add:
            current_notional += additional_notional

    print("[MockTradeEngine] Final notional:", current_notional)


if __name__ == "__main__":
    main()