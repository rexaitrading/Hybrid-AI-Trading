"""
Test script for TradeEngine with Kelly + Risk Adjustment
--------------------------------------------------------
Runs a batch of sample signals across multiple assets to
verify Kelly sizing, risk caps, and execution logic.
"""

import os, sys, yaml

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from hybrid_ai_trading.trade_engine import TradeEngine


def run_tests():
    # --- Load config ---
    with open("config.yaml", "r", encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)

    engine = TradeEngine(cfg)

    # --- Sample signals to test ---
    test_signals = [
        ("BTC/USDT", "BUY", 1, 60000),   # 1 BTC at $60k
        ("ETH/USDT", "BUY", 10, 3000),   # 10 ETH at $3k
        ("SPY", "BUY", 100, 500),        # 100 SPY at $500
        ("BTC/USDT", "SELL", 1, 60000),  # Sell BTC
        ("ETH/USDT", "HOLD", 0, 3000),   # Hold ETH
    ]

    print("\n=== TradeEngine Kelly Test ===")
    for symbol, signal, size, price in test_signals:
        print(f"\n▶️ Signal: {signal} {symbol} @ {price}")
        result = engine.process_signal(symbol, signal, size, price)
        print("Result:", result)


if __name__ == "__main__":
    run_tests()
