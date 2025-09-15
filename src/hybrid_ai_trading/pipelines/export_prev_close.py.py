"""
Export Previous Close Data (Hybrid AI Quant Pro v6.1 – AAA Polished & Coverage Ready)
------------------------------------------------------------------------------------
- Fetches prev close from Polygon (stocks, macro, IPOs, leverage ETFs)
- Fetches batch prev close from CoinAPI (crypto)
- Handles errors gracefully, logs warnings
- Exports to CSV + JSON in ./data
"""

import os
import json
import csv
from datetime import datetime, timezone
from typing import Dict, List, Any

from hybrid_ai_trading.config.settings import load_config
from utils.universe import Core_Stocks, Crypto_Signal, Macro_Risk, Leverage_Tools, IPO_Watch
from hybrid_ai_trading.data.clients.polygon_client import PolygonClient
from hybrid_ai_trading.data.clients.coinapi_client import batch_prev_close


def _ms_to_iso(ms: int) -> str:
    """Convert Polygon's epoch-ms timestamp to ISO UTC string."""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def main():
    # 1) Load config & clients
    cfg = load_config()
    client = PolygonClient()

    # 2) Asset groups
    asset_groups: Dict[str, List[str]] = {
        "Core_Stocks": Core_Stocks,
        "Crypto_Signal": Crypto_Signal,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }

    rows: List[Dict[str, Any]] = []

    # 3) Fetch data for each group
    for group, symbols in asset_groups.items():
        print(f"\n📥 Fetching {group} ({len(symbols)})")

        # --- Crypto handled via CoinAPI batch ---
        if group == "Crypto_Signal":
            try:
                out = batch_prev_close(symbols, quote="USD")
                for s in symbols:
                    r = out.get(s, {})
                    rows.append({
                        "group": group, "symbol": s,
                        "asof": r.get("asof", ""),
                        "open": r.get("open"), "high": r.get("high"),
                        "low": r.get("low"), "close": r.get("close"),
                        "volume": r.get("volume"), "vwap": r.get("vwap"),
                        "status": r.get("status", "NO_DATA"),
                    })
                print(f"✅ {group} done")
            except Exception as e:
                print(f"❌ {group} error: {e}")
            continue  # skip Polygon loop for crypto

        # --- All other groups via Polygon ---
        for symbol in symbols:
            try:
                data = client.prev_close(symbol)
                if "results" in data and data["results"]:
                    r = data["results"][0]
                    row = {
                        "group": group,
                        "symbol": symbol,
                        "asof": _ms_to_iso(r.get("t", 0)),
                        "open": r.get("o"),
                        "high": r.get("h"),
                        "low": r.get("l"),
                        "close": r.get("c"),
                        "volume": r.get("v"),
                        "vwap": r.get("vw"),
                        "status": data.get("status", "OK"),
                    }
                    rows.append(row)
                    print(f"✅ {symbol} close={row['close']} "
                          f"O/H/L={row['open']}/{row['high']}/{row['low']}")
                else:
                    rows.append({
                        "group": group, "symbol": symbol, "asof": "",
                        "open": None, "high": None, "low": None, "close": None,
                        "volume": None, "vwap": None,
                        "status": f"NO_DATA: {data}",
                    })
                    print(f"⚠️ {symbol} no data")
            except Exception as e:
                rows.append({
                    "group": group, "symbol": symbol, "asof": "",
                    "open": None, "high": None, "low": None, "close": None,
                    "volume": None, "vwap": None,
                    "status": f"ERROR: {e}",
                })
                print(f"❌ {symbol} error: {e}")

    # 4) Export CSV & JSON
    os.makedirs("data", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("data", f"prev_close_{stamp}.csv")
    json_path = os.path.join("data", f"prev_close_{stamp}.json")

    headers = ["group", "symbol", "asof", "open", "high", "low", "close",
               "volume", "vwap", "status"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\n📂 Exported:\n- {csv_path}\n- {json_path}")


if __name__ == "__main__":
    main()
