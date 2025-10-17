from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class Signal:
    side: str        # 'BUY', 'SELL', 'FLAT'
    strength: float  # 0..1

def _ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False).mean()

def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([(h - l).abs(),
                    (h - c.shift()).abs(),
                    (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def momo_signal(df: pd.DataFrame, fast: int = 12, slow: int = 26, vol_floor_mult: float = 1.0) -> Signal:
    """
    Momentum+volatility filter:
      - MACD histogram for direction
      - ATR-based activity floor to avoid dead tape
    """
    if len(df) < max(slow, 50) or df[["open","high","low","close"]].isna().any().any():
        return Signal("FLAT", 0.0)

    close = df["close"]
    macd = _ema(close, fast) - _ema(close, slow)
    macd_sig = _ema(macd, 9)
    hist = macd - macd_sig

    atr = _atr(df, 14)
    vol_floor = vol_floor_mult * float(atr.mean())
    recent_range = float(df["high"].tail(20).max() - df["low"].tail(20).min())

    if np.isnan(recent_range) or recent_range < max(vol_floor, 1e-6):
        return Signal("FLAT", 0.0)

    s = float(np.tanh(hist.iloc[-1] * 5.0))  # normalized
    if s > 0.05:
        return Signal("BUY", min(s, 1.0))
    if s < -0.05:
        return Signal("SELL", min(abs(s), 1.0))
    return Signal("FLAT", 0.0)
