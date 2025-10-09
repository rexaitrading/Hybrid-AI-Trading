"""
Hybrid AI Trading – Portfolio Package (Hedge Fund Grade v2.0)
-------------------------------------------------------------
Responsibilities:
- PortfolioTracker: track holdings, equity, and exposure
- Allocation strategies for balancing assets
- Performance metrics and risk analytics
"""

# Expose PortfolioTracker at package level for convenience.
from .portfolio_tracker import PortfolioTracker

__all__ = ["PortfolioTracker"]
