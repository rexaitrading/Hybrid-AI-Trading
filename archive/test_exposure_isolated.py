import importlib
import inspect
import sys

import hybrid_ai_trading.execution.portfolio_tracker as pt_module

print(">>> PortfolioTracker code:\n", inspect.getsource(pt_module.PortfolioTracker))

# 👇 This will show exactly where Python is loading modules from
print(">>> sys.path =", sys.path)

# Force reload to make sure we use the latest file on disk
importlib.reload(pt_module)
PortfolioTracker = pt_module.PortfolioTracker


def test_exposure_isolated():
    pt = PortfolioTracker(100000)
    pt.update_position("AAPL", "BUY", 500, 100)
    pt.update_position("TSLA", "SELL", 300, 200)
    pt.update_equity({"AAPL": 100, "TSLA": 200})
    exposure = pt.get_total_exposure()
    print("DEBUG >>> exposure =", exposure)
    assert exposure == 110000.0
