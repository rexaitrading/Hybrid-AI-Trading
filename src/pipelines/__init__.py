"""
Pipelines package initializer.
Exports pipeline modules for convenience.
"""

from . import backtest, daily_close, paper_trade_demo

__all__ = ["daily_close", "backtest", "paper_trade_demo"]
