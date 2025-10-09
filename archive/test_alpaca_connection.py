"""
Alpaca Connection Test (Hybrid AI Quant Pro v7.4 – Hedge-Fund Grade, Safe & Coverage-Ready)
==========================================================================================
- Loads Alpaca API credentials from .env or environment.
- Safely handles missing keys (skips instead of crashing).
- Tests account connection and order placement (paper trading).
"""

import os

import alpaca_trade_api as tradeapi
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Load environment
# ----------------------------------------------------------------------
load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# ----------------------------------------------------------------------
# Guard for missing keys
# ----------------------------------------------------------------------
if not API_KEY or not API_SECRET:
    print("⚠️  Skipping Alpaca connection test – API keys not set in environment.")
    exit(0)

print("🔑 Using key:", API_KEY[:6] + "..." if API_KEY else "MISSING")
print("🔑 Using secret:", API_SECRET[:6] + "..." if API_SECRET else "MISSING")
print("🌐 Base URL:", BASE_URL)

# ----------------------------------------------------------------------
# Initialize API client
# ----------------------------------------------------------------------
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

# ----------------------------------------------------------------------
# Test account connection
# ----------------------------------------------------------------------
try:
    account = api.get_account()
    print("✅ Account status:", account.status)
    print("💰 Equity:", account.equity)
    print("💵 Cash:", account.cash)
except Exception as e:
    print("❌ Connection failed:", e)

# ----------------------------------------------------------------------
# Test placing a paper order
# ----------------------------------------------------------------------
try:
    order = api.submit_order(
        symbol="AAPL", qty=1, side="buy", type="market", time_in_force="day"
    )
    print("📈 Order submitted:", order)
except Exception as e:
    print("❌ Order failed:", e)
