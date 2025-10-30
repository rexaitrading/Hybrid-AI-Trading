from __future__ import annotations

import argparse
import os
import statistics as stats
from typing import Any, Dict, List, Tuple

try:
    import ccxt
except Exception:
    ccxt = None


def pct(a: float, b: float) -> float:
    return 0.0 if b == 0 else 100.0 * (a - b) / b


def sma(vals: List[float], n: int) -> float:
    return 0.0 if len(vals) < n or n <= 0 else sum(vals[-n:]) / n


def atr(ohlcv: List[List[float]], n: int = 14) -> float:
    if len(ohlcv) < n + 1:
        return 0.0
    trs = []
    pc = float(ohlcv[-(n + 1)][4])
    for row in ohlcv[-n:]:
        h, l, c = float(row[2]), float(row[3]), float(row[4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        pc = c
    return sum(trs) / n


def get_exchange(name: str):
    if ccxt is None:
        return None
    name = (name or "kraken").lower()
    if name == "binance":
        return ccxt.binance()
    if name == "binanceus":
        return ccxt.binanceus()
    return ccxt.kraken()


def map_symbol(symbol: str, ex_name: str) -> str:
    """Map USDC->USDT for binance-style exchanges so we get deep history."""
    if ex_name in ("binance", "binanceus"):
        base, quote = symbol.split("/", 1)
        if quote.upper() == "USDC":
            return f"{base}/USDT"
    return symbol


def fetch_ohlcv_forward(
    ex, symbol: str, tf: str, total: int
) -> Tuple[List[List[float]], int]:
    """
    Forward pagination:
      - start since = now - total * tf_ms
      - fetch in chunks; append strictly increasing bars
    Returns (bars, tf_ms).
    """
    out: List[List[float]] = []
    tf_ms = int(ex.parse_timeframe(tf) * 1000)
    now_ms = ex.milliseconds()
    since = now_ms - total * tf_ms
    last_ts = None
    remaining = total

    while remaining > 0:
        try:
            batch = ex.fetch_ohlcv(
                symbol, timeframe=tf, since=since, limit=min(1000, remaining)
            )
        except Exception:
            break
        if not batch:
            # no data progress; advance window forward and continue
            since += tf_ms * min(1000, remaining)
            if since >= now_ms:
                break
            continue
        # strictly increasing timestamps
        if last_ts is not None:
            batch = [row for row in batch if row and row[0] > last_ts]
        if not batch:
            since += tf_ms * min(1000, remaining)
            if since >= now_ms:
                break
            continue
        out.extend(batch)
        last_ts = out[-1][0]
        remaining = total - len(out)
        since = last_ts + tf_ms
        if since >= now_ms:
            break
    return out, tf_ms


def run_bt(
    symbol: str,
    tf: str = "5m",
    risk_quote: float = 2.0,
    atr_k: float = 2.0,
    min_quote: float = 5.8,
    cap: float = 50.0,
    ex_name: str = "kraken",
    total_bars: int = 1500,
    fee_bps: float = 10.0,
) -> Dict[str, Any]:
    ex = get_exchange(ex_name)
    if ex is None:
        return {"symbol": f"{symbol} [@{ex_name}]", "msg": "no exchange"}
    sym_m = map_symbol(symbol, ex_name)

    ohl, tf_ms = fetch_ohlcv_forward(ex, sym_m, tf, total_bars)
    if len(ohl) < 200:
        return {
            "symbol": f"{symbol} [{sym_m}@{ex_name}]",
            "msg": "insufficient data",
            "bars": len(ohl),
        }

    equity = 1.0
    wins: List[bool] = []
    rets: List[float] = []
    dd = 0.0
    peak = 1.0
    fee_rt = 2 * fee_bps / 10000.0  # round-trip

    # estimate period length (days)
    total_minutes = (len(ohl) * tf_ms) / (1000 * 60)
    period_days = total_minutes / (60 * 24)

    i = 200
    while i < len(ohl):
        window = ohl[:i]
        c = float(window[-1][4])
        s20 = sma([x[4] for x in window], 20)
        s50 = sma([x[4] for x in window], 50)

        # near-high lookback by tf
        win = 78 if tf == "5m" else 26 if tf == "15m" else 360
        highs_src = [x[4] for x in window[-min(len(window), win) :]]
        if not highs_src:
            i += 1
            continue
        high = max(highs_src)
        a = atr(window, 14)

        buy = (s20 > s50) and (abs(pct(c, high)) <= 1.0) and (a > 0.0)
        if not buy:
            i += 1
            continue

        stop = c - atr_k * a
        r = c - stop
        if r <= 0:
            i += 1
            continue

        # ATR size (for sizing UI only); clip to cap
        size_q = max(min_quote, (risk_quote * c) / (atr_k * a))
        if cap > 0:
            size_q = min(size_q, cap)

        # exits: STOP, SMA50, or 2R TP
        tp = c + 2 * r
        j = i + 1
        exitp = c
        while j < len(ohl):
            c2 = float(ohl[j][4])
            s50n = sma([x[4] for x in ohl[: j + 1]], 50)
            if c2 <= stop:
                exitp = stop
                break
            if c2 <= s50n:
                exitp = c2
                break
            if c2 >= tp:
                exitp = tp
                break
            j += 1

        gross = (exitp - c) / c
        net = gross - fee_rt
        rets.append(net)
        wins.append(net > 0)

        # multiplicative equity & drawdown
        equity *= 1.0 + net
        peak = max(peak, equity)
        dd = min(dd, (equity / peak) - 1.0)
        i = j if j > i else i + 1

    n = len(rets)
    if n == 0:
        return {
            "symbol": f"{symbol} [{sym_m}@{ex_name}]",
            "trades": 0,
            "msg": "no trades",
            "bars": len(ohl),
        }

    pos_sum = sum(x for x in rets if x > 0)
    neg_sum = -sum(x for x in rets if x < 0)
    pf = (
        (pos_sum / neg_sum)
        if (pos_sum > 0 and neg_sum > 0)
        else (float("inf") if neg_sum == 0 else 0.0)
    )

    total_ret = equity - 1.0
    cagr = None
    try:
        years = max(1e-6, period_days / 365.25)
        cagr = (equity ** (1 / years)) - 1.0
    except Exception:
        cagr = None

    return {
        "symbol": f"{symbol} [{sym_m}@{ex_name}]",
        "bars": len(ohl),
        "tf": tf,
        "trades": n,
        "win%": round(100 * sum(wins) / n, 1),
        "avgR%": round(100 * (stats.mean(rets) if n else 0.0), 2),
        "PF": round(pf, 2),
        "maxDD%": round(100 * dd, 2),
        "finalEquity": round(equity, 4),
        "periodDays": round(period_days, 2),
        "CAGR%": round(100 * cagr, 2) if cagr is not None else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchange", default=os.getenv("BT_EXCHANGE", "kraken"))
    ap.add_argument("--tf", default=os.getenv("TC_TF", "5m"))
    ap.add_argument("--limit", type=int, default=int(os.getenv("BT_LIMIT", "1500")))
    ap.add_argument(
        "--fee_bps", type=float, default=float(os.getenv("BT_FEE_BPS", "10"))
    )
    ap.add_argument("--atr_k", type=float, default=float(os.getenv("TC_ATR_K", "2.0")))
    ap.add_argument(
        "--risk_q", type=float, default=float(os.getenv("TC_RISK_QUOTE", "2.0"))
    )
    ap.add_argument(
        "--min_q", type=float, default=float(os.getenv("TC_SIZE_HINT_QUOTE", "5.8"))
    )
    ap.add_argument(
        "--cap", type=float, default=float(os.getenv("HG_MAX_TRADE_QUOTE", "50"))
    )
    ap.add_argument("--pairs", default=os.getenv("TC_CRYPTO", "BTC/USDC,ETH/USDC"))
    args = ap.parse_args()

    pairs = [s.strip() for s in str(args.pairs).split(",") if s.strip()]
    for p in pairs:
        res = run_bt(
            p,
            args.tf,
            args.risk_q,
            args.atr_k,
            args.min_q,
            args.cap,
            ex_name=str(args.exchange).lower(),
            total_bars=args.limit,
            fee_bps=args.fee_bps,
        )
        print(res)


if __name__ == "__main__":
    main()
