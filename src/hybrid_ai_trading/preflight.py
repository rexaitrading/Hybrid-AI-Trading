from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

# optional imports
try:
    import ccxt
except Exception:
    ccxt = None
try:
    from hybrid_ai_trading.trade_console import crypto_signal, env_list
except Exception:
    crypto_signal = None

STATE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".runtime", "guard_state.json")
)


def load_guard_today() -> Dict[str, Any]:
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            s = json.load(f)
        day = time.strftime("%Y-%m-%d", time.gmtime())
        return s.get(day, {})
    except Exception:
        return {}


def get_usdc() -> float:
    key = os.getenv("KRAKEN_KEYFILE")
    if not key or not os.path.exists(key):
        return -1.0
    if ccxt is None:
        return -1.0
    try:
        # private ccxt requires key+secret; your executors use a custom loader, so just do a quick public balance check fallback
        # we simulate via your kraken_client path instead (safer)
        from hybrid_ai_trading.data.clients.kraken_client import load_client

        c = load_client()
        b = c.fetch_balance() or {}
        free = b.get("free") or {}
        return float(free.get("USDC", 0) or 0)
    except Exception:
        return -1.0


def main() -> None:
    cap_q = float(os.getenv("HG_MAX_TRADE_QUOTE", "50") or 50)
    daily_not = float(os.getenv("HG_DAILY_NOTIONAL", "0") or 0)
    daily_tr = int(os.getenv("HG_DAILY_TRADES", "0") or 0)
    pairs = (
        env_list("TC_CRYPTO", "BTC/USDC,ETH/USDC")
        if crypto_signal
        else ["BTC/USDC", "ETH/USDC"]
    )

    print("\nPRE-FLIGHT\n----------")
    # Keyfile
    kfile = os.getenv("KRAKEN_KEYFILE")
    print(f"KRAKEN_KEYFILE: {kfile or '(not set)'}")
    if kfile and not os.path.exists(kfile):
        print("  ! Keyfile path does not exist")

    # Balances
    usdc = get_usdc()
    if usdc < 0:
        print("USDC: (unavailable)")
    else:
        print(f"USDC: {usdc:.2f}")

    # LiveGuard room
    today = load_guard_today()
    used_not = float(today.get("notional", 0.0))
    used_tr = int(today.get("trades", 0))
    room_not = "âˆž" if daily_not <= 0 else f"{max(0.0,daily_not - used_not):.2f}"
    room_tr = "âˆž" if daily_tr <= 0 else f"{max(0,daily_tr - used_tr)}"
    print(
        f"LiveGuard caps: per-trade={cap_q}  daily_notional={daily_not}  daily_trades={daily_tr}"
    )
    print(
        f"  used today: notional={used_not:.2f} trades={used_tr}  room: notional={room_not} trades={room_tr}"
    )

    # Signals (clipped)
    print("\nBUYS (clipped)\n---------------")
    if crypto_signal:
        anyb = False
        cap = float(os.getenv("HG_MAX_TRADE_QUOTE", "0") or 0)
        for p in pairs:
            sig = crypto_signal(p)
            if not sig or not sig.get("buy"):
                continue
            eff = (
                min(float(sig["size_quote"]), cap)
                if cap > 0
                else float(sig["size_quote"])
            )
            print(
                f"{p} ({sig['tf']}): entryâ‰ˆ{sig['last']:.2f} sizeâ‰ˆ{eff:.2f} stopâ‰ˆ{(sig['stop'] or float('nan')):.2f}"
            )
            anyb = True
        if not anyb:
            print("(no crypto buys now)")
    else:
        print("(console not importable)")

    # GO / NO-GO
    go = (usdc >= 6.0) if usdc >= 0 else False
    print("\nCHECK\n-----")
    print("GO" if go else "NO-GO: need â‰¥ ~6 USDC (or funding to post)")


if __name__ == "__main__":
    main()
