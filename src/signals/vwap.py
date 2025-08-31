"""
VWAP Strategy

Logic:
- VWAP = cumulative(price * volume) / cumulative(volume)
- BUY  if price < VWAP (potential undervaluation).
- SELL if price > VWAP (potential overvaluation).
- HOLD otherwise.
"""

import pandas as pd
from typing import List, Dict

def vwap_signal(bars: List[Dict]) -> str:
    if len(bars) < 5:
        return "HOLD"

    df = pd.DataFrame(bars)
    df["tpv"] = df["c"] * df["v"]  # typical price * volume
    vwap = df["tpv"].cumsum().iloc[-1] / df["v"].cumsum().iloc[-1]

    price = df["c"].iloc[-1]
    if price < vwap:
        return "BUY"
    elif price > vwap:
        return "SELL"
    return "HOLD"
