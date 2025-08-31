"""
Moving Average Crossover Strategy

Logic:
- BUY if short MA crosses above long MA
- SELL if short MA crosses below long MA
- HOLD otherwise
"""

import pandas as pd
from typing import List, Dict

def moving_average_signal(bars: List[Dict], short_window: int = 5, long_window: int = 20) -> str:
    if len(bars) < long_window + 1:
        return "HOLD"

    closes = pd.Series([b["c"] for b in bars])
    short_ma = closes.rolling(short_window).mean()
    long_ma = closes.rolling(long_window).mean()

    # Ensure enough data
    if short_ma.isna().iloc[-2] or long_ma.isna().iloc[-2]:
        return "HOLD"

    prev_short, prev_long = short_ma.iloc[-2], long_ma.iloc[-2]
    curr_short, curr_long = short_ma.iloc[-1], long_ma.iloc[-1]

    if prev_short <= prev_long and curr_short > curr_long:
        return "BUY"
    if prev_short >= prev_long and curr_short < curr_long:
        return "SELL"
    return "HOLD"
