"""
Breakout Strategy (Intraday)

Logic:
- BUY if current close > max(highs) of lookback window
- SELL if current close < min(lows) of lookback window
- HOLD otherwise
"""

def breakout_intraday(bars, lookback: int = 20):
    if len(bars) < lookback + 1:
        return "HOLD"

    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]

    recent_close = closes[-1]
    if recent_close > max(highs[-lookback:]):
        return "BUY"
    if recent_close < min(lows[-lookback:]):
        return "SELL"
    return "HOLD"
