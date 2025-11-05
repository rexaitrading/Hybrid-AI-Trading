"""
ETH 1h Alpha Signal (trend + breakout + EMA200 Â± K*ATR thrust, ATR clamp)
Returns: "BUY" / "SELL" / None
Bars: [[ts, o, h, l, c, v], ...]
"""

from typing import List, Optional

# --- Tunables (safe defaults) ---
BREAKOUT_N = 24
ATR_MIN = 0.003  # 0.3%
ATR_MAX = 0.03  # 3.0%
K_ATR = 0.5  # thrust buffer vs EMA200


def _ema_last(values: List[float], period: int) -> Optional[float]:
    n = len(values)
    if n < period:
        return None
    k = 2.0 / (period + 1.0)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1.0 - k)
    return ema


def _atr_last(
    highs: List[float], lows: List[float], closes: List[float], period: int = 14
) -> Optional[float]:
    n = len(closes)
    if n < period + 1:
        return None
    trs = []
    for i in range(n - period, n):
        prev_close = closes[i - 1]
        tr = max(
            highs[i] - lows[i], abs(highs[i] - prev_close), abs(lows[i] - prev_close)
        )
        trs.append(tr)
    return sum(trs) / float(period)


def eth1h_signal(bars: List[List[float]]) -> Optional[str]:
    if not bars or len(bars) < 210:
        return None

    highs = [b[2] for b in bars if b[2] is not None]
    lows = [b[3] for b in bars if b[3] is not None]
    closes = [b[4] for b in bars if b[4] is not None]
    if min(len(highs), len(lows), len(closes)) < 210:
        return None

    ema50 = _ema_last(closes, 50)
    ema200 = _ema_last(closes, 200)
    atr14 = _atr_last(highs, lows, closes, 14)
    last = closes[-1] if closes else None

    if ema50 is None or ema200 is None or atr14 is None or last is None or last <= 0:
        return None

    atr_pct = atr14 / last
    if not (ATR_MIN <= atr_pct <= ATR_MAX):
        return None

    # Prior window (exclude the current bar)
    if len(highs) <= BREAKOUT_N:
        return None
    prev_high = max(highs[-(BREAKOUT_N + 1) : -1])
    prev_low = min(lows[-(BREAKOUT_N + 1) : -1])

    long_trend = ema50 > ema200
    short_trend = ema50 < ema200

    breakout_up = last > prev_high
    breakdown_dn = last < prev_low
    thrust_up = last > (ema200 + K_ATR * atr14)
    thrust_down = last < (ema200 - K_ATR * atr14)

    # Longs: uptrend + (breakout OR thrust above EMA200 by K*ATR)
    if long_trend and (breakout_up or thrust_up):
        return "BUY"

    # Shorts: downtrend + (breakdown OR thrust below EMA200 by K*ATR)
    if short_trend and (breakdown_dn or thrust_down):
        return "SELL"

    return None
