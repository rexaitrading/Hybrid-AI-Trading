import math
from typing import List, Optional

try:
    import ccxt
except Exception as e:
    print("ccxt import error:", e); raise

# --- helpers (match your alpha) ---
def _ema_last(values: List[float], period: int) -> Optional[float]:
    n = len(values)
    if n < period: return None
    k = 2.0 / (period + 1.0)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1.0 - k)
    return ema

def _atr_last(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    n = len(closes)
    if n < period + 1: return None
    trs = []
    for i in range(n - period, n):
        prev_close = closes[i - 1]
        trs.append(max(highs[i] - lows[i], abs(highs[i] - prev_close), abs(lows[i] - prev_close)))
    return sum(trs) / float(period)

def main():
    ex = ccxt.binance()
    ex.load_markets()
    bars = ex.fetch_ohlcv("ETH/USDT", timeframe="1h", limit=1000)

    highs = [b[2] for b in bars if b[2] is not None]
    lows  = [b[3] for b in bars if b[3] is not None]
    closes= [b[4] for b in bars if b[4] is not None]

    ema50  = _ema_last(closes, 50)
    ema200 = _ema_last(closes, 200)
    atr14  = _atr_last(highs, lows, closes, 14)
    last   = closes[-1] if closes else None

    prev_high_24 = max(highs[-25:-1]) if len(highs) >= 25 else None
    prev_low_24  = min(lows[-25:-1])  if len(lows)  >= 25 else None

    atr_pct = (atr14 / last) if (atr14 and last) else None

    print("Bars:", len(bars))
    print("Last:", last)
    print("EMA50:", ema50)
    print("EMA200:", ema200)
    print("Trend up? ", (ema50 is not None and ema200 is not None and ema50 > ema200))
    print("Prev 24h High:", prev_high_24, "Prev 24h Low:", prev_low_24)
    print("Breakout up?  ", (last is not None and prev_high_24 is not None and last > prev_high_24))
    print("Breakdown?    ", (last is not None and prev_low_24  is not None and last < prev_low_24))
    print("ATR14:", atr14, "ATR%:", (None if atr_pct is None else round(100*atr_pct, 3)))
    print("ATR clamp OK? ", (atr_pct is not None and 0.003 <= atr_pct <= 0.03))
    # quick decision echo (same as alpha logic)
    decision = None
    if ema50 and ema200 and last and prev_high_24 and prev_low_24 and atr_pct is not None and 0.003 <= atr_pct <= 0.03:
        if ema50 > ema200 and last > prev_high_24:
            decision = "BUY"
        elif ema50 < ema200 and last < prev_low_24:
            decision = "SELL"
    print("Alpha decision now:", decision)

if __name__ == "__main__":
    main()