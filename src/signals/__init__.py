"""
Signal Strategies Package
Exports all supported trading strategies in one namespace:
- Breakout
- Moving Average Crossover
- RSI
- Bollinger Bands
- MACD
- VWAP
"""

# src/signals/__init__.py

from .breakout_intraday import breakout_intraday
from .moving_average import moving_average_signal
from .rsi_signal import rsi_signal
from .bollinger_bands import bollinger_bands_signal
from .macd import macd_signal
from .vwap import vwap_signal

# Strategy registry
STRATEGIES = {
    "breakout": breakout_intraday,
    "ma": moving_average_signal,
    "rsi": rsi_signal,
    "bollinger": bollinger_bands_signal,
    "macd": macd_signal,
    "vwap": vwap_signal,
}
