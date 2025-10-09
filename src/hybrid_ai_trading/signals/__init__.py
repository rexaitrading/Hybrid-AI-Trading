"""
Hybrid AI Quant Pro – Signals Registry
--------------------------------------
Central export hub for all trading signal strategies.

Purpose:
- Provide a unified STRATEGIES dict for pipelines and tests.
- Guarantee hedge-fund-grade consistency across all signal modules.
"""

from .bollinger_bands import bollinger_bands_signal
from .breakout_intraday import breakout_intraday
from .breakout_polygon import BreakoutPolygonSignal
from .breakout_v1 import breakout_v1
from .macd import macd_signal
from .moving_average import moving_average_signal
from .rsi_signal import rsi_signal
from .vwap import vwap_signal

# ----------------------------------------------------------------------
# Strategy Registry
# ----------------------------------------------------------------------
STRATEGIES = {
    "bollinger": lambda symbol, bars=None: bollinger_bands_signal(bars or []),
    "breakout_intraday": lambda symbol, bars=None: breakout_intraday(bars or []),
    "breakout_polygon": lambda symbol, bars=None: BreakoutPolygonSignal().generate(
        symbol, bars=bars or []
    ),
    "breakout_v1": lambda symbol, bars=None: breakout_v1(bars or []),
    "macd": lambda symbol, bars=None: macd_signal(bars or []),
    "ma": lambda symbol, bars=None: moving_average_signal(bars or []),
    "rsi": lambda symbol, bars=None: rsi_signal(bars or []),
    "vwap": lambda symbol, bars=None: vwap_signal(bars or []),
}

__all__ = ["STRATEGIES"]
