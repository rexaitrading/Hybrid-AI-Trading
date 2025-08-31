"""
RSI Strategy

Logic:
- BUY if RSI < 30 (oversold bounce)
- SELL if RSI > 70 (overbought reversal)
- HOLD otherwise
"""

import pandas as pd
from typing import List, Dict

def rsi_signal(bars: List[Dict], period: int = 14) -> str:
    if len(bars) < period + 1:
        return "HOLD"

    closes = pd.Series([b["c"] for b in bars])
    delta = closes.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]

    if pd.isna(avg_gain) or pd.isna(avg_loss) or avg_loss == 0:
        return "HOLD"

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    if rsi < 30:
        return "BUY"
    elif rsi > 70:
        return "SELL"
    return "HOLD"
