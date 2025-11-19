from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from tools.orb_vwap_gatescore_filter import filter_trades
from hybrid_ai_trading.trade_engine_phase5_skeleton import (
    TradeEnginePhase5,
    AddDecision,
)
from hybrid_ai_trading.risk_manager_phase5_bridge import (
    PositionSnapshot,
    AddRequest,
)


def _load_thresholds(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_trades(jsonl_path: str) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            trades.append(json.loads(line))
    return trades


def main() -> None:
    # 1) Read thresholds (AAPL ORB/VWAP)
    cfg_path = os.path.join("config", "orb_vwap_spy_thresholds.json")
    thresholds = _load_thresholds(cfg_path)
    print("[SPY-PHASE5-SIM] Loaded thresholds:", thresholds)

    # 2) Load enriched trades
    jsonl_path = os.path.join("research", "spy_orb_vwap_replay_trades_enriched.jsonl")
    trades = _load_trades(jsonl_path)
    print(f"[SPY-PHASE5-SIM] Loaded {len(trades)} enriched trade(s) from {jsonl_path}")

    # 3) Gate signals via orb_vwap_gatescore_filter logic
    gated = filter_trades(trades, thresholds)
    print(f"[SPY-PHASE5-SIM] {len(gated)} trade(s) passed GateScore + cost filters.")

    if not gated:
        print("[SPY-PHASE5-SIM] No trades passed the gate; nothing to simulate.")
        return

    # 4) Wire in TradeEnginePhase5: consider_add() before simulated add
    engine = TradeEnginePhase5()
    print("[SPY-PHASE5-SIM] Using RiskConfig:", engine.risk_manager.risk_cfg)
    print("[SPY-PHASE5-SIM] Using CostConfig:", engine.risk_manager.cost_cfg)

    current_notional = 0.0

    for idx, t in enumerate(gated, start=1):
        symbol = t.get("symbol", "SPY")
        side = "LONG"  # ORB/VWAP AAPL = BUY in this gated sample
        pnl_pct = float(t.get("pnl_pct", 0.0))
        unrealized_pnl_bp = pnl_pct * 10_000.0

        base_notional = float(t.get("cost_notional") or 10_000.0)
        if current_notional == 0.0:
            current_notional = base_notional
        additional_notional = base_notional
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

        decision: AddDecision = engine.consider_add(pos, add_req)

        print(
            f"[SPY-PHASE5-SIM] trade #{idx} "
            f"symbol={symbol} "
            f"pnl_pct={pnl_pct:.4f} "
            f"unrealized_pnl_bp={unrealized_pnl_bp:.2f} "
            f"notional={current_notional:.0f} "
            f"add_notional={additional_notional:.0f} "
            f"-> can_add={decision.can_add} reason={decision.reason}"
        )

        # Simulated order: only 'add' if gate says okay
        if decision.can_add:
            current_notional += additional_notional

    print("[SPY-PHASE5-SIM] Final simulated notional:", current_notional)


if __name__ == "__main__":
    main()