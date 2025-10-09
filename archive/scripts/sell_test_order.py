# scripts/sell_test_order.py
"""
Sell Test Order – Hybrid AI Trading (Polished v2)
------------------------------------------------
✅ Cancels open orders before selling
✅ Uses Alpaca close_position() to avoid wash trade
✅ Falls back to bracket order if needed
"""

import os

import alpaca_trade_api as tradeapi
from dotenv import load_dotenv

# Load .env credentials
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

try:
    # --- Cancel any open AAPL orders ---
    open_orders = api.list_orders(status="open")
    for order in open_orders:
        if order.symbol == "AAPL":
            print(f"🛑 Canceling open order: {order.id}")
            api.cancel_order(order.id)

    # --- Get current position ---
    position = api.get_position("AAPL")
    qty = abs(int(float(position.qty)))
    avg_entry = float(position.avg_entry_price)
    print(f"📊 Current AAPL position: {qty} shares @ {avg_entry}. Closing...")

    # --- Try direct close ---
    try:
        result = api.close_position("AAPL")
        print("✅ Closed via close_position:", result)
    except Exception as e1:
        print("❌ Primary close failed:", e1)
        # --- Fallback: bracket order ---
        try:
            order = api.submit_order(
                symbol="AAPL",
                qty=qty,
                side="sell",
                type="limit",
                time_in_force="day",
                order_class="bracket",
                limit_price=round(avg_entry * 1.00, 2),  # close near entry
                take_profit={"limit_price": round(avg_entry * 1.01, 2)},
                stop_loss={"stop_price": round(avg_entry * 0.99, 2)},
            )
            print("✅ Fallback bracket close submitted:", order)
        except Exception as e2:
            print("❌ Final close failed:", e2)

except Exception as e:
    print("❌ No AAPL position found:", e)
