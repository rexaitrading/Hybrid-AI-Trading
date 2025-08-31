"""
MACD Strategy

Logic:
- MACD = EMA(12) - EMA(26)
- Signal line = EMA(9) of MACD
- BUY  if MACD crosses above Signal.
- SELL if MACD crosses below Signal.
- HOLD otherwise.
"""

import pandas as pd
from typing import List, Dict

def macd_signal(bars: List[Dict], fast: int = 12, slow: int = 26, signal_window: int = 9) -> str:
    closes = pd.Series([b["c"] for b in bars])
    if len(closes) < slow + signal_window:
        return "HOLD"

    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_window, adjust=False).mean()

    if macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
        return "BUY"
    elif macd.iloc[-2] > signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]:
        return "SELL"
    return "HOLD"
