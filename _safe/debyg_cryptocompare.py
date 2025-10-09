"""
debyg_cryptocompare.py
------------------------------------------------------------
One-shot fetch from CryptoCompare for debugging / sanity checks.
Polished Hedge-Fund Grade: Safe API key handling, logging, and output.
"""

import os
import sys
import json
import requests
from typing import Any


# === API Key Handling =====================================================
API_KEY: str | None = os.getenv("CRYPTOCOMPARE_API_KEY")
if not API_KEY:
    print(
        "❌ Missing CryptoCompare API key.\n"
        "Set it with:\n"
        '   setx CRYPTOCOMPARE_API_KEY "your_key_here"\n'
        "Then restart your terminal / shell and re-run this script."
    )
    sys.exit(1)


# === Main Debug Fetch =====================================================
def main() -> None:
    """Fetch BTC, ETH, SOL prices in USD and pretty-print the result."""
    url = "https://min-api.cryptocompare.com/data/pricemulti"
    params = {"fsyms": "BTC,ETH,SOL", "tsyms": "USD"}
    headers = {"authorization": f"Apikey {API_KEY}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print("🌐 HTTP status:", response.status_code)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        print("\n✅ Parsed result:")
        print(json.dumps(data, indent=2))
    except requests.exceptions.RequestException as net_err:
        print("❌ Network error:", repr(net_err))
        sys.exit(1)
    except (ValueError, json.JSONDecodeError) as parse_err:
        print("❌ JSON parse error:", repr(parse_err))
        sys.exit(1)
    except Exception as e:
        print("❌ Unexpected error:", repr(e))
        sys.exit(1)


# === Entrypoint ===========================================================
if __name__ == "__main__":
    main()
