"""
Demo: Breakout + Black Swan Guard + Risk Manager + Mock Execution
Now using real Polygon breakout signal and logging results to CSV.
"""

import csv
import os

from dotenv import load_dotenv

from src.config.settings import load_config
from src.risk.black_swan_guard import BlackSwanGuard
from src.risk.risk_manager import RiskManager
from src.signals.breakout_polygon import breakout_signal_polygon

# Load .env and config
load_dotenv()
cfg = load_config()


class MockBroker:
    def place_order(self, symbol: str, side: str, qty: int = 1):
        print(f"[MOCK ORDER] {side.upper()} {qty} {symbol}")
        return {"status": "submitted", "symbol": symbol, "side": side, "qty": qty}


def run_demo(symbol_id="AAPL", qty=1, guard=None, writer=None):
    risk = RiskManager()
    guard = guard or BlackSwanGuard()
    broker = MockBroker()

    # Step 1: Generate raw signal
    raw_signal = breakout_signal_polygon(symbol_id)
    print(f"\n--- {symbol_id} ---")
    print(f"Raw Signal: {raw_signal}")

    # Step 2: Black Swan Guard
    guarded_signal = guard.filter_signal(raw_signal)
    print(f"After Black Swan Guard: {guarded_signal}")

    # Step 3: Risk Manager
    final_signal = risk.control_signal(guarded_signal)
    print(f"After Risk Manager: {final_signal}")

    # Step 4: Execute
    executed = None
    if final_signal in ["BUY", "SELL"]:
        order = broker.place_order(symbol_id, final_signal.lower(), qty)
        executed = order["status"]
        print("Execution Result:", order)
    else:
        print("No trade executed (signal = HOLD)")
        executed = "no_trade"

    # Log to CSV if writer is provided
    if writer:
        writer.writerow(
            {
                "symbol": symbol_id,
                "raw_signal": raw_signal,
                "guarded_signal": guarded_signal,
                "final_signal": final_signal,
                "executed": executed,
            }
        )


if __name__ == "__main__":
    # Prepare CSV log
    os.makedirs("logs", exist_ok=True)
    logfile = "logs/demo_results.csv"

    with open(logfile, mode="w", newline="") as f:
        fieldnames = [
            "symbol",
            "raw_signal",
            "guarded_signal",
            "final_signal",
            "executed",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        print("=== DEMO RUN WITHOUT BLACK SWAN ===")
        for stock in cfg["universe"]["stocks"]:
            run_demo(stock, writer=writer)
        for crypto in cfg["universe"]["crypto"]:
            run_demo(crypto, writer=writer)
        for forex in cfg["universe"]["forex"]:
            run_demo(forex, writer=writer)

        print("\n=== DEMO RUN WITH BLACK SWAN TRIGGERED ===")
        guard = BlackSwanGuard()
        guard.trigger_event("news_sentiment_ai", "Crash detected")
        run_demo("AAPL", guard=guard, writer=writer)

    print(f"\n✅ Demo results logged to {logfile}")
