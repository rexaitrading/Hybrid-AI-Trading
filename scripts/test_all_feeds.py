"""
Test All Feeds (Hybrid AI Quant Pro v1.0)
-----------------------------------------
Checks API connectivity for:
- Polygon (equities / ETFs)
- CoinAPI (crypto)
- Benzinga (news)
- Alpaca (broker + market data)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def check_polygon():
    key = os.getenv("POLYGON_API_KEY") or os.getenv("POLYGON_KEY")
    if not key:
        return "❌ Polygon key missing"
    url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey={key}"
    r = requests.get(url)
    return f"Polygon: {r.status_code} | {r.json().get('status', 'no status')}"


def check_coinapi():
    key = os.getenv("COINAPI_KEY")
    if not key:
        return "❌ CoinAPI key missing"
    url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
    headers = {"X-CoinAPI-Key": key}
    r = requests.get(url, headers=headers)
    return f"CoinAPI: {r.status_code} | BTC/USD={r.json().get('rate', 'no rate')}"


def check_benzinga():
    key = os.getenv("BENZINGA_KEY")
    if not key:
        return "❌ Benzinga key missing"
    url = f"https://api.benzinga.com/api/v2/news?token={key}&symbols=AAPL&limit=1"
    r = requests.get(url)

    try:
        data = r.json()
    except Exception:
        return f"Benzinga: {r.status_code} | ❌ Invalid response (not JSON)"

    if isinstance(data, list) and data:
        headline = data[0].get("title", "no title")
    else:
        headline = "no news"

    return f"Benzinga: {r.status_code} | Latest headline: {headline}"



def check_alpaca():
    key = os.getenv("ALPACA_KEY")
    secret = os.getenv("ALPACA_SECRET")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    if not key or not secret:
        return "❌ Alpaca keys missing"

    # Check account status
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    r = requests.get(f"{base_url}/v2/account", headers=headers)
    if r.status_code == 200:
        account = r.json()
        return f"Alpaca: {r.status_code} | Account status={account.get('status')}, Cash=${account.get('cash')}"
    return f"Alpaca: {r.status_code} | {r.text}"


if __name__ == "__main__":
    print("=== FEED STATUS CHECK ===")
    print(check_polygon())
    print(check_coinapi())
    print(check_benzinga())
    print(check_alpaca())
