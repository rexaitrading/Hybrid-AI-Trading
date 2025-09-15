# scripts/check_alpaca_positions.py
import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load environment
load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

print("🔑 Key:", API_KEY[:6] + "...")
print("🌐 Base URL:", BASE_URL)

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

# --- Check account ---
try:
    account = api.get_account()
    print("✅ Account status:", account.status)
    print("💰 Equity:", account.equity, "| 💵 Cash:", account.cash)
except Exception as e:
    print("❌ Failed to get account:", e)

# --- Check open orders ---
try:
    orders = api.list_orders(status="all", limit=5)
    print("\n📋 Recent Orders:")
    if not orders:
        print("   No orders found.")
    for o in orders:
        print(f"   {o.symbol} | {o.side.upper()} {o.qty} | {o.status} | {o.submitted_at}")
except Exception as e:
    print("❌ Failed to get orders:", e)

# --- Check positions ---
try:
    positions = api.list_positions()
    print("\n📊 Current Positions:")
    if not positions:
        print("   No open positions.")
    for p in positions:
        print(f"   {p.symbol} | Qty: {p.qty} | Avg Entry: {p.avg_entry_price} | Unrealized PnL: {p.unrealized_pl}")
except Exception as e:
    print("❌ Failed to get positions:", e)
