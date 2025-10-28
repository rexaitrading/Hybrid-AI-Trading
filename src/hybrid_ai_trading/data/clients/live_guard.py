from __future__ import annotations

"""
LiveGuard (Hybrid AI Quant Pro v1.0) - simple per-trade & daily caps
- Env caps (all optional):
  HG_MAX_TRADE_QUOTE   (e.g., 50)   # Kraken quote currency per trade
  HG_MAX_TRADE_SHARES  (e.g., 5)    # IBKR shares per trade
  HG_DAILY_NOTIONAL    (e.g., 200)  # total per day in quote currency (Kraken)
  HG_DAILY_TRADES      (e.g., 20)   # total number of trades per day (both)
State file: .runtime/guard_state.json
"""
import json
import os
import time
from typing import Any, Dict

STATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "..",
    "..",
    "..",
    ".runtime",
    "guard_state.json",
)
STATE = os.path.normpath(STATE)


def _load_state() -> Dict[str, Any]:
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(s: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


def _today_key() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def check(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    context:
      broker: "kraken" | "ibkr"
      symbol: "BTC/USDC" | "AAPL" ...
      side: "BUY" | "SELL"
      notional_quote: float | None   # Kraken: quote spend (USDC). IBKR: optional.
      shares: float | None           # IBKR: share count. Kraken: None.
    Returns {"ok": True} or {"ok": False, "error": "...", "hint": "..."}
    """
    s = _load_state()
    day = _today_key()
    day_state = s.setdefault(day, {"notional": 0.0, "trades": 0})
    # read caps
    max_trade_quote = float(os.getenv("HG_MAX_TRADE_QUOTE", "0") or 0)
    max_trade_shares = float(os.getenv("HG_MAX_TRADE_SHARES", "0") or 0)
    daily_notional = float(os.getenv("HG_DAILY_NOTIONAL", "0") or 0)
    daily_trades = int(os.getenv("HG_DAILY_TRADES", "0") or 0)

    broker = str(context.get("broker", "")).lower()
    symbol = str(context.get("symbol", ""))
    side = str(context.get("side", "")).upper()
    notional = float(context.get("notional_quote") or 0.0)
    shares = float(context.get("shares") or 0.0)

    # per-trade caps
    if broker == "kraken" and max_trade_quote > 0 and notional > max_trade_quote:
        return {
            "ok": False,
            "error": "cap_violation",
            "hint": f"Reduce quote to <= {max_trade_quote:.2f}",
        }
    if broker == "ibkr" and max_trade_shares > 0 and shares > max_trade_shares:
        return {
            "ok": False,
            "error": "cap_violation",
            "hint": f"Reduce shares to <= {max_trade_shares:.2f}",
        }

    # daily counts
    if daily_trades > 0 and (day_state["trades"] + 1) > daily_trades:
        return {
            "ok": False,
            "error": "daily_trades_limit",
            "hint": f"Limit {daily_trades} reached today",
        }

    if (
        broker == "kraken"
        and daily_notional > 0
        and (day_state["notional"] + notional) > daily_notional
    ):
        return {
            "ok": False,
            "error": "daily_notional_limit",
            "hint": f"Daily notional cap {daily_notional:.2f} reached",
        }

    # pass: update state
    day_state["trades"] += 1
    if broker == "kraken":
        day_state["notional"] += notional
    s[day] = day_state
    _save_state(s)
    return {"ok": True}
