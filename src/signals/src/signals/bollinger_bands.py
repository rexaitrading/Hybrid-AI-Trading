"""
Bollinger Bands Strategy

Logic:
- Uses 20-period moving average with ±2 standard deviation bands.
- BUY  if price closes below lower band (oversold).
- SELL if price closes above upper band (overbought).
- HOLD otherwise.
"""

import pandas as pd
from typing import List, Dict

def bollinger_bands_signal(bars: List[Dict], window: int = 20, num_std: float = 2.0) -> str:
    if len(bars) < window:
        return "HOLD"

    closes = pd.Series([b["c"] for b in bars])
    sma = closes.rolling(window).mean().iloc[-1]
    std = closes.rolling(window).std().iloc[-1]

    upper_band = sma + num_std * std
    lower_band = sma - num_std * std
    price = closes.iloc[-1]

    if price < lower_band:
        return "BUY"
    elif price > upper_band:
        return "SELL"
    return "HOLD"
