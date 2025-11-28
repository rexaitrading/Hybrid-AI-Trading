from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def run_trades(rm: RiskManager) -> List[Dict[str, Any]]:
    """
    Run two SPY ORB LIVE test trades through RiskManager.check_trade_phase5
    and collect decision + EV metadata.

    Trades:
    - tp_r = 2.0
    - tp_r = 1.5
    """
    base = {
        "symbol": "SPY",
        "regime": "SPY_ORB_LIVE",
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
        "day_id": "TEST_DAY",
    }

    trades: List[Dict[str, Any]] = []
    for tp_r in (2.0, 1.5):
        trade = dict(base)
        trade["tp_r"] = tp_r

        decision = rm.check_trade_phase5(trade)
        if not isinstance(decision, Phase5RiskDecision):
            details = {}
            allowed = True
            reason = "decision_not_phase5"
        else:
            details = decision.details or {}
            allowed = decision.allowed
            reason = decision.reason

        ev_mu = details.get("ev_mu")
        ev_band_abs = details.get("ev_band_abs")

        trades.append(
            {
                "trade": trade,
                "allowed": allowed,
                "reason": reason,
                "ev": ev_mu,
                "ev_band_abs": ev_band_abs,
            }
        )

    return trades


def main() -> None:
    rm = RiskManager()
    rows = run_trades(rm)

    out_path = Path("logs") / "spy_phase5_ev_test.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "ts",
        "symbol",
        "regime",
        "side",
        "qty",
        "price",
        "tp_r",
        "ev",
        "ev_band_abs",
        "phase5_allowed",
        "phase5_reason",
    ]

    ts = datetime.now(timezone.utc).isoformat()

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            trade = row["trade"]
            writer.writerow(
                {
                    "ts": ts,
                    "symbol": trade["symbol"],
                    "regime": trade["regime"],
                    "side": trade["side"],
                    "qty": trade["qty"],
                    "price": trade["price"],
                    "tp_r": trade["tp_r"],
                    "ev": row["ev"],
                    "ev_band_abs": row["ev_band_abs"],
                    "phase5_allowed": row["allowed"],
                    "phase5_reason": row["reason"],
                }
            )

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()