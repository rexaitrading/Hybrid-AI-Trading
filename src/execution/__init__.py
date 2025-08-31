"""
Execution package initializer.
Exports core execution modules for cleaner imports.
"""

from .order_manager import OrderManager
from .portfolio_tracker import PortfolioTracker
from .paper_simulator import PaperSimulator

__all__ = ["OrderManager", "PortfolioTracker", "PaperSimulator"]
