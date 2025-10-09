"""
Export Previous Close (Hybrid AI Quant Pro – Hedge-Fund Grade, Timezone Aware)
- Exports daily prev_close for Core_Stocks and Core_Crypto.
- Writes CSV + JSON outputs under ./data/.
- Stub fallback: if Polygon key missing, logs warning but still exits 0.
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from hybrid_ai_trading.data.clients.coinapi_client import batch_prev_close
from hybrid_ai_trading.data.clients.polygon_client import PolygonAPIError, PolygonClient

logger = logging.getLogger("hybrid_ai_trading.pipelines.export_prev_close")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

DATA_DIR = "data"
Core_Crypto = ["BTC/USDT", "ETH/USDT"]
Core_Stocks = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN"]


def _ms_to_iso(ms: Any) -> str:
    """Convert ms timestamp to an ISO-8601 string in UTC (Z-suffixed)."""
    try:
        ts = int(ms) / 1000.0
        iso = datetime.fromtimestamp(ts, timezone.utc).isoformat()
        # normalize +00:00 to Z (optional, cosmetic)
        return iso.replace("+00:00", "Z")
    except Exception:
        return ""


def _safe_export(path: str, rows: Any, mode: str = "csv") -> None:
    """Export rows safely to CSV/JSON with error handling."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if mode == "csv":
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
        logger.info("Exported %s", path)
    except Exception as e:
        logger.error("Export failed: %s", e)


def main() -> None:
    all_rows: list[Dict[str, Any]] = []

    # --- Crypto via CoinAPI ---
    try:
        crypto = batch_prev_close(Core_Crypto, quote="USD")
        for sym, d in crypto.items():
            all_rows.append(
                {
                    "symbol": sym,
                    "asof": d.get("asof", ""),
                    "open": d.get("open"),
                    "high": d.get("high"),
                    "low": d.get("low"),
                    "close": d.get("close"),
                    "volume": d.get("volume"),
                    "vwap": d.get("vwap"),
                    "status": d.get("status", "UNKNOWN"),
                }
            )
    except Exception as e:
        logger.error("batch_prev_close failed: %s", e)

    # --- Stocks via Polygon ---
    try:
        client = PolygonClient(allow_missing=True)  # allow stub mode
        for sym in Core_Stocks:
            try:
                data = client.prev_close(sym)
                results = data.get("results", []) if isinstance(data, dict) else []
                if results:
                    bar = results[0]
                    all_rows.append(
                        {
                            "symbol": sym,
                            "asof": _ms_to_iso(bar.get("t")),
                            "open": bar.get("o"),
                            "high": bar.get("h"),
                            "low": bar.get("l"),
                            "close": bar.get("c"),
                            "volume": bar.get("v"),
                            "vwap": bar.get("vw"),
                            "status": "OK",
                        }
                    )
                else:
                    all_rows.append(
                        {
                            "symbol": sym,
                            "asof": "",
                            "open": None,
                            "high": None,
                            "low": None,
                            "close": None,
                            "volume": None,
                            "vwap": None,
                            "status": "NO_DATA",
                        }
                    )
            except Exception as e:
                logger.error("Polygon prev_close failed for %s: %s", sym, e)
                all_rows.append(
                    {
                        "symbol": sym,
                        "asof": "",
                        "open": None,
                        "high": None,
                        "low": None,
                        "close": None,
                        "volume": None,
                        "vwap": None,
                        "status": f"ERROR:{e}",
                    }
                )
    except PolygonAPIError as e:
        logger.warning("PolygonClient unavailable: %s", e)

    # --- Final Export ---
    if all_rows:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        csv_path = os.path.join(DATA_DIR, f"prev_close_{ts}.csv")
        json_path = os.path.join(DATA_DIR, f"prev_close_{ts}.json")
        _safe_export(csv_path, all_rows, "csv")
        _safe_export(json_path, all_rows, "json")

    sys.exit(0)


if __name__ == "__main__":
    main()
