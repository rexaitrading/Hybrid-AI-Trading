from __future__ import annotations

"""
NVDA Phase-5 live-style runner (no IBG side effects in this template).

- Uses real ExecutionEngine with a minimal config.
- Calls place_order_phase5_with_logging(...) once for NVDA.
- Exercises:
  * Phase-5 decisions gate (should_allow_trade)
  * RiskManager.phase5_no_averaging_down_for_symbol adapter
  * Logging to logs/phase5_live_events.jsonl and optional paper_exec_logger.
"""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.execution.execution_engine import (
    ExecutionEngine,
    place_order_phase5_with_logging,
)
from hybrid_ai_trading.risk.risk_phase5_account_caps import account_daily_loss_gate


IPO_WATCHLIST_PATH = Path("logs") / "ipo_watchlist.jsonl"


def load_ipo_tags() -> Dict[str, Dict[str, Any]]:
    """
    Load IPO tags from logs/ipo_watchlist.jsonl produced by tools/update_ipo_watchlist.py.

    Returns: symbol -> dict with keys:
      - origin_region
      - is_hk_origin
      - is_international
      - phase5_candidate
      - phase5_notes
    """
    tags: Dict[str, Dict[str, Any]] = {}
    if not IPO_WATCHLIST_PATH.exists():
        return tags

    with IPO_WATCHLIST_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            symbol = str(entry.get("symbol", "")).upper()
            if not symbol:
                continue
            tags[symbol] = entry
    return tags


def get_account_daily_loss_cap_from_env(default: float = 50.0) -> float:
    """
    Read Phase-5 account daily loss cap from env var HAT_PHASE5_ACCOUNT_DAILY_LOSS_CAP.

    Returns default (e.g. $50) if unset or invalid.
    """
    value = os.environ.get("HAT_PHASE5_ACCOUNT_DAILY_LOSS_CAP")
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def build_live_config() -> Dict[str, Any]:
    """
    Phase-5 NVDA live config for IB paper trading.

    NOTE:
    - dry_run=False: ExecutionEngine will use broker adapter (IB paper).
    - Broker/account/port are read from env vars where possible.
    - Make sure IB Gateway PAPER is up and env vars are set before running.
    """
    return {
        "dry_run": False,
        "phase5_no_averaging_down_enabled": True,
        "phase5": {
            "no_averaging_down_enabled": True,
            "account_daily_loss_cap": get_account_daily_loss_cap_from_env(50.0),
        },
        "broker": {
            "adapter": "ib",
            "host": os.environ.get("HAT_IB_HOST", "127.0.0.1"),
            "port": int(os.environ.get("HAT_IB_PORT", "7497")),
            "client_id": int(os.environ.get("HAT_IB_CLIENT_ID", "42")),
            "account": os.environ.get("HAT_IB_ACCOUNT", "DUXXXXXXXX"),
            "paper": True,
        },
        "universe": ["NVDA"],
        "costs": {
            "mode": "simple_bps",
            "commission_bps": 0.5,
            "slippage_bps": 1.0,
        },
    }


def main() -> None:
    cfg = build_live_config()

    print("=== nvda_phase5_live_runner ===")
    print("Config:", cfg)

    # Phase-5 account daily loss gate at start of runner (assume realized PnL = 0 for this smoke).
    account_cap = cfg.get("phase5", {}).get("account_daily_loss_cap", 0.0)
    daily_gate = account_daily_loss_gate(
        account_realized_pnl=0.0,
        account_daily_loss_cap=account_cap,
    )
    if not daily_gate.allowed:
        print("\n[PHASE5] Account daily loss gate BLOCKED at start of runner:")
        print("  reason =", daily_gate.reason)
        print("  details=", getattr(daily_gate, "details", None))
        return

    # Build ExecutionEngine with config-only constructor.
    try:
        engine = ExecutionEngine(config=cfg)  # adjust if your ctor differs
    except TypeError as e:
        print("\n[WARN] ExecutionEngine(config=...) ctor failed with TypeError:")
        print("      ", e)
        print("      Adjust build_live_config() / ctor usage to match your engine.")
        return
    except Exception as e:
        print("\n[WARN] ExecutionEngine ctor failed:", e)
        return

    # Synthetic entry timestamp close to "now".
    # In a real live strategy, use the actual bar/signal timestamp.
    entry_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Dummy NVDA trade parameters for this runner.
    # Real live logic will drive side/qty/price from signals + Kelly sizing.
    symbol = "NVDA"
    side = "BUY"
    qty = 1.0
    price = 1.0  # dummy price for IB paper connectivity smoke (must be > 0)
    regime = "NVDA_BPLUS_LIVE"

    # Load IPO tags (for future IPO symbols, including HK-origin NASDAQ listings).
    ipo_tags = load_ipo_tags()
    ipo_info = ipo_tags.get(symbol.upper())

    if ipo_info:
        print("\n[IPO] Tags for", symbol, ":")
        print("  origin_region    =", ipo_info.get("origin_region"))
        print("  is_hk_origin     =", ipo_info.get("is_hk_origin"))
        print("  is_international =", ipo_info.get("is_international"))
        print("  phase5_candidate =", ipo_info.get("phase5_candidate"))
        print("  phase5_notes     =", ipo_info.get("phase5_notes"))

    print("\nCalling place_order_phase5_with_logging(...)")
    print("  symbol   =", symbol)
    print("  entry_ts =", entry_ts)
    print("  side     =", side)
    print("  qty      =", qty)
    print("  regime   =", regime)

    result = place_order_phase5_with_logging(
        engine,
        symbol=symbol,
        entry_ts=entry_ts,
        side=side,
        qty=qty,
        price=price,
        regime=regime,
    )

    print("\nResult from place_order_phase5_with_logging:")
    print(result)

    # Optional Phase-5 no-averaging-down demo: second BUY in same process.
    # Enabled only when HAT_PHASE5_DOUBLE_BUY_DEMO=1 to avoid changing normal behavior.
    import os as _os
    if _os.environ.get("HAT_PHASE5_DOUBLE_BUY_DEMO") == "1":
        print("\n[Phase5] Calling SECOND place_order_phase5_with_logging(...) to demo no-averaging-down")
        result2 = place_order_phase5_with_logging(
            engine,
            symbol=symbol,
            entry_ts=entry_ts,
            side=side,
            qty=qty,
            price=price,
            regime=regime,
        )
        print("\n[Phase5] Result from SECOND place_order_phase5_with_logging:")
        print(result2)
    print("\nIf wiring is correct, you should see a new event in:")
    print("  logs/phase5_live_events.jsonl")
    print("and, if paper_exec_logger.log_phase5_event/log_event exists,")
    print("  it will also be forwarded there.")
    print("\nTo move from small IB paper probe -> fuller live setup:")
    print("  - replace dummy price/qty with real signal- and Kelly-driven values")
    print("  - extend cfg['broker'] / cfg['costs'] / universe as needed")
    print("  - keep this runner under Phase-5 risk + PreMarket guardrails")


if __name__ == "__main__":
    main()