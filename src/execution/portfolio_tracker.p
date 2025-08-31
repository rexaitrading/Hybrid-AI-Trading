import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class PortfolioTracker:
    def __init__(self):
        self.positions = defaultdict(float)
        self.cash = 100000  # starting demo equity
        self.history = []

    def update_position(self, symbol, side, size, price):
        value = size * price
        if side == "buy":
            self.positions[symbol] += size
            self.cash -= value
        else:
            self.positions[symbol] -= size
            self.cash += value
        self.history.append((symbol, side, size, price))
        logger.info(f"Updated {symbol}: pos={self.positions[symbol]}, cash={self.cash}")
