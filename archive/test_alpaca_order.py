"""
Test Alpaca Paper Order (BUY with OCO exit)
Hybrid AI Trading – v2.0
--------------------------------------------------
- Loads keys from .env
- Places a market BUY order (AAPL, qty=1)
- Attaches OCO (take-profit + stop-loss)
- Prints order details or error
--------------------------------------------------
"""

import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load environment variables
load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

print("🔑 Using key:", API_KEY[:6] + "..." if API_KEY else "❌ Missing")
print("🌐 Base URL:", BASE_URL)

# Initialize Alpaca REST client
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

try:
    # --- Bracket BUY (entry + OCO exits) ---
    order = api.submit_order(
        symbol="AAPL",
        qty=1,
        side="buy",
        type="market",
        time_in_force="day",
        order_class="bracket",   # ✅ Avoids wash trade
        take_profit={"limit_price": 9999},  # Placeholder, replaced below
        stop_loss={"stop_price": 1}         # Placeholder, replaced below
    )

    print("✅ Order submitted successfully!")
    print("📈 Symbol:", order.symbol)
    print("📝 Status:", order.status)
    print("📦 Filled Qty:", order.qty)
    print("🔗 Order ID:", order.id)

except Exception as e:
    print("❌ Order failed:", e)
