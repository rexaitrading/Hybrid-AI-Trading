import os
import requests
from dotenv import load_dotenv

# Load keys from .env
load_dotenv()
API_KEY = os.getenv("POLYGON_KEY")

def get_prev_bar(ticker: str):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={API_KEY}"
    resp = requests.get(url, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"Polygon API error {resp.status_code}: {resp.text[:200]}")

    return resp.json()


if __name__ == "__main__":
    ticker = "AAPL"
    data = get_prev_bar(ticker)
    print("Status Code:", 200)
    print("Response:", data)
