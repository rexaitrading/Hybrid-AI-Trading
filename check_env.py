import os

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Environment variables to check (not raw keys!)
keys = [
    "POLYGON_KEY",
    "COINAPI_KEY",
    "ALPACA_KEY",
    "ALPACA_SECRET",
    "BENZINGA_KEY",
    "IBKR_ACCOUNT",
    "BINANCE_API_KEY",
]

for key in keys:
    value = os.getenv(key)
    if value:
        print(f"{key} present ✅, preview: ******{value[-6:]}")  # only show last 6 chars
    else:
        print(f"{key} MISSING ❌")
