"""
Quant Engine Tester
Simulates trades and shows Kelly fraction + metrics adapting in real time
"""

import yaml
from hybrid_ai_trading.trade_engine import TradeEngine


def run_test():
    with open("config.yaml", "r", encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)

    engine = TradeEngine(cfg)

    # Simulate trades
    test_trades = [
        ("BTC/USDT", "BUY", 1, 60000, +500),   # win $500
        ("ETH/USDT", "BUY", 10, 3000, -200),   # loss $200
        ("SPY", "BUY", 100, 500, +100),        # win $100
        ("BTC/USDT", "SELL", 1, 60000, -300),  # loss $300
    ]

    for symbol, side, size, price, pnl in test_trades:
        result = engine.process_signal(symbol, side, size, price)
        engine.performance_tracker.record_trade(pnl)
        engine.performance_tracker.record_equity(engine.get_equity())
        print(f"\nSignal: {side} {symbol} @ {price}")
        print("Result:", result)
        print(f"WinRate={engine.performance_tracker.win_rate():.2f} | "
              f"Payoff={engine.performance_tracker.payoff_ratio():.2f} | "
              f"Sharpe={engine.performance_tracker.sharpe_ratio():.2f} | "
              f"Sortino={engine.performance_tracker.sortino_ratio():.2f}")


if __name__ == "__main__":
    run_test()
