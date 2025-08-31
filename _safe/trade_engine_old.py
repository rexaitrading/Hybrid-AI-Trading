"""
Trade Engine

Connects:
- Signal layer (e.g., breakout strategy)
- Risk layer (RiskManager)
- Execution layer (broker/exchange client)
"""

import os
import requests
from src.signals.breakout_v1 import breakout_signal
from src.risk.risk_manager import RiskManager


class MockAlpacaClient:
    """
    Mock Alpaca client for order execution.
    Replace with real Alpaca API integration later.
    """
    def __init__(self):
        self.api_key = os.getenv("ALPACA_KEY", "FAKE_KEY")
        self.api_secret = os.getenv("ALPACA_SECRET", "FAKE_SECRET")
        self.base_url = "https://paper-api.alpaca.markets/v2"

    def place_order(self, symbol: str, side: str, qty: int = 1):
        """
        Mock placing an order.
        In production: send POST request to Alpaca API.
        """
        print(f"[MOCK EXECUTION] {side} {qty} {symbol}")
        return {"status": "submitted", "symbol": symbol, "side": side, "qty": qty}


class TradeEngine:
    def __init__(self):
        self.risk_manager = RiskManager()
        self.broker = MockAlpacaClient()

    def run_strategy(self, symbol_id: str, qty: int = 1):
        """
        Run breakout strategy, filter by risk, and send to execution layer.
        """
        # 1. Generate signal
        raw_signal = breakout_signal(symbol_id)
        print(f"Raw signal: {raw_signal}")

        # 2. Risk Manager gate
        final_signal = self.risk_manager.control_signal(raw_signal)
        print(f"Risk-filtered signal: {final_signal}")

        # 3. Execute if allowed
        if final_signal in ["BUY", "SELL"]:
            order = self.broker.place_order(symbol_id, final_signal.lower(), qty)
            print(f"Order result: {order}")
            return order

        print("No trade executed.")
        return {"status": "no_trade", "symbol": symbol_id}
