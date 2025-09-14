from hybrid_ai_trading.trade_engine import TradeEngine
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker

cfg = {"dry_run": True, "risk": {"equity": 100000}}
te = TradeEngine(cfg, portfolio=PortfolioTracker(100000))

result = te.process_signal("AAPL", "BUY", price=150, size=50, algo="twap")
print(result)
