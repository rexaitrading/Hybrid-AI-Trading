from __future__ import annotations
import os, sys
from hybrid_ai_trading.order_manager import OrderManager

def main(symbol: str = "AAPL", qty: float = 2.0):
    print("BACKEND:", os.getenv("BROKER_BACKEND", "fake"))
    om = OrderManager()
    om.start()
    res = om.buy_market(symbol, qty)
    print("buy_market:", res)
    print("positions:", om.positions())
    om.stop()

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    q = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    main(sym, q)