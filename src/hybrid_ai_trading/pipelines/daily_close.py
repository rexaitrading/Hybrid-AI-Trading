"""
Daily Close Exporter (Hybrid AI Quant Pro v6.8 Ã¢â‚¬â€œ OE Grade, Polished)
---------------------------------------------------------------------
- Fetches daily prev close data for stocks (Polygon) and crypto (CoinAPI).
- Groups assets into Core_Stocks, Core_Crypto, Macro, Leverage ETFs, IPO Watch.
- Handles API errors gracefully, logs warnings/errors.
- Exports results to CSV + JSON in ./data folder.
"""

import csv
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from hybrid_ai_trading.data.clients.coinapi_client import batch_prev_close
from hybrid_ai_trading.data.clients.polygon_client import PolygonClient
from hybrid_ai_trading.utils.universe import (
    Core_Crypto,
    Core_Stocks,
    IPO_Watch,
    Leverage_Tools,
    Macro_Risk,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _ms_to_iso(ms: int) -> str:
    """Convert Polygon's epoch-ms timestamp to ISO UTC string."""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return ""


# ----------------------------------------------------------------------
# Main Exporter
# ----------------------------------------------------------------------
def main() -> None:
    client = PolygonClient()

    asset_groups: Dict[str, List[str]] = {
        "Core_Stocks": Core_Stocks,
        "Core_Crypto": Core_Crypto,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }

    rows: List[Dict[str, Any]] = []

    for group, symbols in asset_groups.items():
        logger.info("Ã°Å¸â€œÂ¥ Fetching %s (%d)", group, len(symbols))

        if group == "Core_Crypto":
            try:
                out = batch_prev_close(symbols, quote="USD")
                for s in symbols:
                    r = out.get(s, {})
                    rows.append(
                        {
                            "group": group,
                            "symbol": s,
                            "asof": r.get("asof", ""),
                            "open": r.get("open"),
                            "high": r.get("high"),
                            "low": r.get("low"),
                            "close": r.get("close"),
                            "volume": r.get("volume"),
                            "vwap": r.get("vwap"),
                            "status": r.get("status", "NO_DATA"),
                        }
                    )
                logger.info("Ã¢Å“â€¦ %s complete", group)
            except Exception as e:
                logger.error("Ã¢ÂÅ’ %s error: %s", group, e)
            continue

        # Stock / ETF assets
        for symbol in symbols:
            try:
                data = client.prev_close(symbol)
                if "results" in data and data["results"]:
                    r = data["results"][0]
                    rows.append(
                        {
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
                    )
                    logger.info("Ã¢Å“â€¦ %s close=%s", symbol, r.get("c"))
                else:
                    rows.append(
                        {
                            "group": group,
                            "symbol": symbol,
                            "asof": "",
                            "open": None,
                            "high": None,
                            "low": None,
                            "close": None,
                            "volume": None,
                            "vwap": None,
                            "status": f"NO_DATA: {data}",
                        }
                    )
                    logger.warning("Ã¢Å¡Â Ã¯Â¸Â %s no data", symbol)
            except Exception as e:
                rows.append(
                    {
                        "group": group,
                        "symbol": symbol,
                        "asof": "",
                        "open": None,
                        "high": None,
                        "low": None,
                        "close": None,
                        "volume": None,
                        "vwap": None,
                        "status": f"ERROR: {e}",
                    }
                )
                logger.error("Ã¢ÂÅ’ %s error: %s", symbol, e)

    # ------------------------------------------------------------------
    # Export results
    # ------------------------------------------------------------------
    os.makedirs("data", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("data", f"daily_close_{stamp}.csv")
    json_path = os.path.join("data", f"daily_close_{stamp}.json")

    headers = [
        "group",
        "symbol",
        "asof",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "status",
    ]

    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        logger.info("Ã°Å¸â€œâ€š Exported:\n- %s\n- %s", csv_path, json_path)
    except Exception as e:
        logger.error("Ã¢ÂÅ’ Export failed: %s", e)
        return


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    main()
