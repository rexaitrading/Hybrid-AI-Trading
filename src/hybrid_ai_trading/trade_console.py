from __future__ import annotations

"""
Trade Console (Hybrid AI Quant Pro v1.4 - Discipline-First, ATR Stops, LiveGuard, Kraken SELLs)
-----------------------------------------------------------------------------------------------
- RISK: regime, leverage allowed, black-swan flag
- BUYS: only entries that pass breakout + ATR + caps (size clipped to HG_MAX_TRADE_QUOTE)
- NEAR: candidates close to breakout
- SELLS: actual Kraken holdings that violate SMA50 or ATR stop
- WATCH: IPO/watchlist (optional CSV)

Env examples:
  TC_CRYPTO="BTC/USDC,ETH/USDC"     TC_TF="5m"   TC_ATR_K="2.0"   TC_RISK_QUOTE="2.0"   TC_SIZE_HINT_QUOTE="5.8"
  TC_BLACK_SWAN_BTC_DROP="8"         TC_MAX_LEVERAGE="1"
  HG_MAX_TRADE_QUOTE="50"            # Kraken per-trade cap
  KRAKEN_KEYFILE="C:\\HybridAITrading\\kraken_api.json"
  TC_WATCH_IPO_CSV="data/ipo_watchlist.csv"
"""

import os
from typing import Any, Dict, List, Optional

# public kraken data (closes/ohlcv)
try:
    import ccxt
except Exception:
    ccxt = None

# IBKR positions (optional)
try:
    from hybrid_ai_trading.data.clients.ibkr_client import connect_ib
    from hybrid_ai_trading.data.clients.ibkr_ops import positions as ibkr_positions
except Exception:
    ibkr_positions = None
    connect_ib = None

# LiveGuard (optional caps)
try:
    from hybrid_ai_trading.data.clients.live_guard import check as live_guard_check
except Exception:
    live_guard_check = None

# Kraken private client for balances
try:
    from hybrid_ai_trading.data.clients.kraken_client import load_client as load_kraken
except Exception:
    load_kraken = None


# ---------------- helpers ----------------
def env_list(name: str, default: str) -> List[str]:
    v = os.getenv(name, default)
    return [s.strip() for s in v.split(",") if s.strip()]


def pct(a: float, b: float) -> float:
    return 0.0 if b == 0 else 100.0 * (a - b) / b


def safe_float(x: Any, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d


def print_section(name: str) -> None:
    bar = "-" * len(name)
    print(f"\n{name}\n{bar}")


def print_line(line: str) -> None:
    print(line)


# ---------------- crypto data & signals ----------------
def fetch_ohlcv_kraken(
    symbol: str, timeframe: str = "1h", limit: int = 200
) -> List[List[float]]:
    if ccxt is None:
        return []
    ex = ccxt.kraken()
    try:
        return ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception:
        return []


def fetch_last_kraken(symbol: str) -> Optional[float]:
    if ccxt is None:
        return None
    ex = ccxt.kraken()
    try:
        t = ex.fetch_ticker(symbol)
        return safe_float(t.get("last") or (t.get("info", {}).get("c", [0])[0]))
    except Exception:
        return None


def sma(vals: List[float], n: int) -> float:
    return 0.0 if len(vals) < n or n <= 0 else sum(vals[-n:]) / n


def atr_from_ohlcv(ohlcv: List[List[float]], period: int = 14) -> float:
    n = len(ohlcv)
    if n < period + 1:
        return 0.0
    trs: List[float] = []
    prev_close = safe_float(ohlcv[-(period + 1)][4])
    for row in ohlcv[-period:]:
        high = safe_float(row[2])
        low = safe_float(row[3])
        close = safe_float(row[4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = close
    return sum(trs) / float(period)


def crypto_signal(symbol: str) -> Optional[Dict[str, Any]]:
    """
    BUY if SMA20 > SMA50 and close within 1% of recent high.
    SELL trigger = (close < SMA50) or (close < stop = last - k*ATR).
    Includes ATR(14), stop, ATR-based size (clipped later by cap).
    """
    tf = os.getenv("TC_TF", "5m")
    lookback = 480 if tf in ("5m", "15m") else 400
    ohlcv = fetch_ohlcv_kraken(symbol, timeframe=tf, limit=lookback)
    if not ohlcv:
        return None

    closes = [safe_float(c[4]) for c in ohlcv]
    last = closes[-1]
    sma20_v = sma(closes, 20)
    sma50_v = sma(closes, 50)

    win = 78 if tf == "5m" else 26 if tf == "15m" else 360
    recent = closes[-win:] if len(closes) >= win else closes
    high_n = max(recent)
    dist = pct(last, high_n)

    atr = atr_from_ohlcv(ohlcv, period=14)
    k = safe_float(os.getenv("TC_ATR_K", "2.0"), 2.0)
    stop = last - k * atr if atr > 0 else None

    r = safe_float(os.getenv("TC_RISK_QUOTE", "2.0"), 2.0)
    min_q = safe_float(os.getenv("TC_SIZE_HINT_QUOTE", "5.8"), 5.8)
    size_q = (r * last / (k * atr)) if (k > 0 and atr > 0 and last > 0) else r
    size_q = max(min_q, size_q)

    buy = (sma20_v > sma50_v) and (abs(dist) <= 1.0)
    sell_trig = (last < sma50_v) or (stop is not None and last < stop)

    return {
        "symbol": symbol,
        "tf": tf,
        "last": last,
        "sma20": sma20_v,
        "sma50": sma50_v,
        "atr": atr,
        "stop": stop,
        "size_quote": size_q,
        "near_breakout": abs(dist) <= 1.0,
        "buy": buy,
        "sell": sell_trig,
        "reason": (
            "SMA20>SMA50 & near high"
            if buy
            else ("Below SMA50/ATR stop" if sell_trig else "Neutral")
        ),
    }


# ---------------- risk / black swan ----------------
def black_swan_crypto(pairs: List[str]) -> Dict[str, Any]:
    thr = safe_float(os.getenv("TC_BLACK_SWAN_BTC_DROP", "8"))
    if ccxt is None or not pairs:
        return {"risk_off": False, "metric": None, "threshold": thr}
    sym = pairs[0]
    ohlcv = fetch_ohlcv_kraken(sym, timeframe="1h", limit=26)
    if len(ohlcv) < 26:
        return {"risk_off": False, "metric": None, "threshold": thr}
    last = safe_float(ohlcv[-1][4])
    prev24 = safe_float(ohlcv[-25][4])
    drop = -pct(last, prev24)
    return {"risk_off": drop >= thr, "metric": drop, "threshold": thr}


# ---------------- holdings (Kraken & IBKR) ----------------
def load_kraken_holdings(pairs: List[str]) -> Dict[str, float]:
    """
    Returns base-asset free amounts for the given pairs, e.g., {"BTC": 0.01, "ETH": 0.2}.
    Requires KRAKEN_KEYFILE + ccxt.kraken private connection.
    """
    if load_kraken is None:
        return {}
    try:
        c = load_kraken()
        bal = c.fetch_balance() or {}
        free = bal.get("free") or {}
        bases = {p.split("/")[0].upper() for p in pairs}
        out: Dict[str, float] = {}
        for asset in bases:
            amt = safe_float(free.get(asset, 0.0))
            if amt > 0:
                out[asset] = amt
        return out
    except Exception:
        return {}


def load_ibkr_positions_list() -> List[Dict[str, Any]]:
    if connect_ib is None or ibkr_positions is None:
        return []
    try:
        ib = connect_ib(readonly=True, timeout=3.0)
        try:
            return ibkr_positions(ib)
        finally:
            ib.disconnect()
    except Exception:
        return []


# ---------------- console main ----------------
def main() -> None:
    crypto_pairs = env_list("TC_CRYPTO", "BTC/USDC,ETH/USDC")
    stocks_list = env_list("TC_STOCKS", "")
    max_lev = safe_float(os.getenv("TC_MAX_LEVERAGE", "1"))
    ipo_csv = os.getenv("TC_WATCH_IPO_CSV", "")

    # RISK
    risk = black_swan_crypto(crypto_pairs)
    print_section("RISK")
    if risk["risk_off"]:
        print_line(
            f"BLACK SWAN: BTC 24h drop Ã¢â€°Ë† {risk['metric']:.1f}% Ã¢â€°Â¥ {risk['threshold']:.1f}% -> NO NEW BUYS"
        )
        lev = 0.0
    else:
        print_line("Regime: NORMAL")
        lev = min(max_lev, 1.0)
    print_line(f"Leverage allowed: {lev:.1f}x")

    # BUYS (caps enforced; size clipped to HG_MAX_TRADE_QUOTE)
    print_section("BUYS")
    any_buy = False
    near: List[Dict[str, Any]] = []
    suppressed: List[Dict[str, Any]] = []
    cap = safe_float(os.getenv("HG_MAX_TRADE_QUOTE", "0"))

    for pair in crypto_pairs:
        sig = crypto_signal(pair)
        if not sig:
            continue
        # collect NEAR
        if sig["near_breakout"] and not sig["buy"]:
            near.append({"pair": pair, "last": sig["last"], "sma50": sig["sma50"]})

        if risk["risk_off"]:
            continue

        if sig["buy"]:
            eff_size = float(sig["size_quote"])
            if cap > 0 and eff_size > cap:
                eff_size = cap
            if live_guard_check:
                guard = live_guard_check(
                    {
                        "broker": "kraken",
                        "symbol": pair,
                        "side": "BUY",
                        "notional_quote": eff_size,
                        "shares": None,
                    }
                )
                if not guard.get("ok", True):
                    suppressed.append({"pair": pair, "reason": guard})
                    continue
            any_buy = True
            stop_txt = f"{sig['stop']:.2f}" if sig["stop"] is not None else "n/a"
            print_line(
                f"{pair} ({sig['tf']}): BUY  entryÃ¢â€°Ë†{sig['last']:.2f}  sizeÃ¢â€°Ë†{eff_size:.2f}  "
                f"stopÃ¢â€°Ë†{stop_txt}  (ATR={sig['atr']:.2f})  {sig['reason']}"
            )

    if not any_buy:
        print_line("(no crypto buys today)")
        if near:
            print_line("NEAR:")
            for it in near[:5]:
                print_line(
                    f"  {it['pair']}: lastÃ¢â€°Ë†{it['last']:.2f} stopÃ¢â€°Ë†SMA50 {it['sma50']:.2f}"
                )
    if suppressed:
        print_line("SUPPRESSED (caps):")
        for it in suppressed[:5]:
            print_line(f"  {it['pair']}: {it['reason']}")

    # SELLS (Kraken holdings + simple rule)
    print_section("SELLS")
    sells_printed = False
    kr_hold = load_kraken_holdings(crypto_pairs)
    if kr_hold:
        for pair in crypto_pairs:
            base, quote = pair.split("/", 1)
            amt = kr_hold.get(base.upper(), 0.0)
            if amt <= 0:
                continue
            sig = crypto_signal(pair)
            if not sig:
                continue
            # SELL if our rule triggers (below SMA50 or below ATR stop)
            if sig["sell"]:
                sells_printed = True
                stop_txt = f"{sig['stop']:.2f}" if sig["stop"] is not None else "n/a"
                print_line(
                    f"{pair}: SELL  qtyÃ¢â€°Ë†{amt:.8f}  lastÃ¢â€°Ë†{sig['last']:.2f}  stopÃ¢â€°Ë†{stop_txt}  ({sig['reason']})"
                )
    else:
        print_line("(no Kraken holdings or KRAKEN_KEYFILE not set)")

    # (Optional) IBKR holdings print (still placeholder)
    pos = load_ibkr_positions_list()
    if pos:
        # Show holdings; you can wire stock SELL rules later
        for p in pos:
            sym = str(p.get("symbol"))
            if stocks_list and sym not in stocks_list:
                continue
            print_line(f"IBKR HOLD: {sym}: {p.get('position')} @ {p.get('avgCost')}")
            sells_printed = True

    if not sells_printed and not kr_hold and not pos:
        # already printed the "(no Kraken holdings ...)" above
        pass

    # WATCH
    print_section("WATCH")
    if ipo_csv and os.path.exists(ipo_csv):
        try:
            rows = [
                r.strip()
                for r in open(ipo_csv, "r", encoding="utf-8").read().splitlines()
                if r.strip()
            ]
            for r in rows[:10]:
                print_line(f"IPO: {r}")
            if len(rows) == 0:
                print_line("(empty IPO list)")
        except Exception:
            print_line("(unable to read IPO watchlist)")
    else:
        print_line("(no IPO file configured)")

    print()


if __name__ == "__main__":
    main()
# --------------- optional loop (print only changes) ---------------
import time
from datetime import datetime


def _active_window() -> bool:
    h = int(datetime.now().strftime("%H"))
    m = int(datetime.now().strftime("%M"))
    return (h > 6 or (h == 6 and m >= 0)) and (h < 21 or (h == 21 and m == 0))


def _snapshot() -> Dict[str, Any]:
    out = {"buys": [], "sells": []}
    pairs = env_list("TC_CRYPTO", "BTC/USDC,ETH/USDC")
    risk = black_swan_crypto(pairs)
    if risk.get("risk_off"):
        return out
    cap = safe_float(os.getenv("HG_MAX_TRADE_QUOTE", "0"))
    for p in pairs:
        sig = crypto_signal(p)
        if not sig:
            continue
        if sig.get("buy"):
            eff = (
                min(float(sig["size_quote"]), cap)
                if cap > 0
                else float(sig["size_quote"])
            )
            out["buys"].append(
                {
                    "p": p,
                    "size": round(eff, 2),
                    "stop": round(sig["stop"], 2) if sig["stop"] else None,
                }
            )
        if sig.get("sell"):
            out["sells"].append({"p": p})
    return out


def run_loop():
    poll = int(os.getenv("TC_POLL_SECS", "60"))
    last = None
    print(f"(looping every {poll}s; prints only changes)")
    while True:
        try:
            if _active_window():
                cur = _snapshot()
                if cur != last:
                    print_section("ALERTS")
                    if cur["buys"]:
                        for b in cur["buys"]:
                            print_line(
                                f"BUY {b['p']} sizeÃ¢â€°Ë†{b['size']} stopÃ¢â€°Ë†{b['stop']}"
                            )
                    else:
                        print_line("(no buys)")
                    if cur["sells"]:
                        for s in cur["sells"]:
                            print_line(f"SELL {s['p']}")
                    else:
                        print_line("(no sells)")
                    last = cur
            else:
                # print once per hour at most when idle
                pass
            time.sleep(poll)
        except KeyboardInterrupt:
            print_line("loop stopped")
            break


if __name__ == "__main__" and "--loop" in os.sys.argv:
    run_loop()
