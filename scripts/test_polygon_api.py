import os
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY")

# Pick a symbol
ticker = "AAPL"

# Build URL for last 5 daily bars
url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/2024-01-01/2025-01-01?limit=5&apiKey={POLYGON_KEY}"

print("URL:", url)

# Call API
resp = requests.get(url)
print("Status:", resp.status_code)
print("Response:", resp.json())
