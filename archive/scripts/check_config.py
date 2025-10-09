import os

from src.config.settings import load_config

cfg = load_config()
print("✅ Config loaded successfully\n")

print("Trading Window:", cfg["trading_window"])
print("Universe (stocks):", cfg["universe"]["stocks"])
print("IPO Watchlist:", cfg["universe"]["ipo_watchlist"])
print("Black Swan Sources:", cfg["features"]["black_swan_sources"])

print("\n✅ Environment keys check")
for key in [
    "POLYGON_KEY",
    "ALPACA_KEY",
    "ALPACA_SECRET",
    "COINAPI_KEY",
    "BENZINGA_KEY",
]:
    print(f"{key}: {'SET' if os.getenv(key) else 'MISSING'}")
