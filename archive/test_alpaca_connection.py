import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load .env file
load_dotenv()

# Get credentials
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

print("🔑 Using key:", API_KEY[:6] + "...")
print("🔑 Using secret:", API_SECRET[:6] + "...")
print("🌐 Base URL:", BASE_URL)

# Initialize API client
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

# --- Test account connection ---
try:
    account = api.get_account()
    print("✅ Account status:", account.status)
    print("💰 Equity:", account.equity)
    print("💵 Cash:", account.cash)
except Exception as e:
    print("❌ Connection failed:", e)

# --- Test placing a paper order ---
try:
    order = api.submit_order(
        symbol="AAPL",
        qty=1,
        side="buy",
        type="market",
        time_in_force="day"
    )
    print("📈 Order submitted:", order)
except Exception as e:
    print("❌ Order failed:", e)
