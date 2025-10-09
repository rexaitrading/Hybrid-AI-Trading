"""
Hybrid AI Quant Pro – Signal Strategies Package (Hedge-Fund Grade)
------------------------------------------------------------------
Exports all supported trading strategies in one namespace:

- Breakout Intraday
- Breakout Polygon
- Breakout V1 (CoinAPI)
- Moving Average Crossover
- RSI
- Bollinger Bands
- MACD
- VWAP
"""

from typing import Callable, Dict

from .bollinger_bands import BollingerBandsSignal
from .breakout_intraday import BreakoutIntradaySignal
from .breakout_polygon import BreakoutPolygonSignal
from .breakout_v1 import BreakoutV1Signal
from .macd import MACDSignal
from .moving_average import MovingAverageSignal
from .rsi_signal import RSISignal
from .vwap import VWAPSignal

# ✅ Central registry: maps strategy names → .generate methods
STRATEGIES: Dict[str, Callable] = {
    "breakout_intraday": BreakoutIntradaySignal().generate,
    "breakout_polygon": BreakoutPolygonSignal().generate,
    "breakout_v1": BreakoutV1Signal().generate,
    "ma": MovingAverageSignal().generate,
    "rsi": RSISignal().generate,
    "bollinger": BollingerBandsSignal().generate,
    "macd": MACDSignal().generate,
    "vwap": VWAPSignal().generate,
}

__all__ = [
    "BreakoutIntradaySignal",
    "BreakoutPolygonSignal",
    "BreakoutV1Signal",
    "MovingAverageSignal",
    "RSISignal",
    "BollingerBandsSignal",
    "MACDSignal",
    "VWAPSignal",
    "STRATEGIES",
]
