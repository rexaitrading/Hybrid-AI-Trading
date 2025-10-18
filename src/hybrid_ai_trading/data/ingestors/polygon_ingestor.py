"""
Polygon Ingestor for Hybrid AI Trading System (Quant Pro v5.1 – Hedge Fund Grade)
--------------------------------------------------------------------------------
Responsibilities:
- Continuously fetch OHLCV bars from Polygon.io
- Store data in both SQLite DB and CSV backup
- Prevent duplicates with UNIQUE constraint
- Handle IntegrityError gracefully (skip duplicates)
- Structured logging for monitoring
"""

import csv
import logging
import os
import time
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from hybrid_ai_trading.data.clients.polygon_client import PolygonClient
from hybrid_ai_trading.data.store.database import Price, SessionLocal, init_db

# ---------------------------
# Logging Setup
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def run_polygon_ingestor(
    interval: int = 60,
    symbol: str = "AAPL",
    start: str = "2024-01-01",
    end: str = None,
    outfile: str = "data/price_feed.csv",
):
    """
    Continuously fetches OHLCV bars from Polygon and stores them into DB + CSV.

    Parameters
    ----------
    interval : int
        Seconds between fetches.
    symbol : str
        Ticker symbol (default = "AAPL").
    start : str
        Start date (YYYY-MM-DD).
    end : str
        End date (YYYY-MM-DD, defaults to today).
    outfile : str
        CSV backup file path.
    """

    client = PolygonClient()
    init_db()
    session = SessionLocal()

    os.makedirs(os.path.dirname(outfile), exist_ok=True)

    # Ensure CSV header exists
    if not os.path.exists(outfile):
        with open(outfile, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "symbol", "open", "high", "low", "close", "volume"])

    logger.info("✅ Database initialized at data/hybrid_ai_trading.db")
    logger.info("🔎 Starting Polygon price ingestor for %s", symbol)
    logger.info("Logging to %s every %ss", outfile, interval)

    while True:
        try:
            end_date = end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            bars = client.get_daily_ohlcv(symbol=symbol, start=start, end=end_date)

            if not bars or not bars.get("results"):
                logger.warning("No OHLCV data fetched for %s", symbol)
            else:
                new_rows = []
                for b in bars["results"]:
                    try:
                        ts = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc)

                        # DB insert with duplicate-safe handling
                        price = Price(
                            timestamp=ts,
                            symbol=symbol,
                            open=b["o"],
                            high=b["h"],
                            low=b["l"],
                            close=b["c"],
                            volume=b["v"],
                        )

                        session.add(price)
                        session.commit()

                        # Add to CSV rows
                        new_rows.append(
                            [
                                ts.isoformat(),
                                symbol,
                                b["o"],
                                b["h"],
                                b["l"],
                                b["c"],
                                b["v"],
                            ]
                        )

                    except IntegrityError:
                        session.rollback()
                        logger.debug("Duplicate skipped: %s %s", symbol, ts)
                    except Exception as inner_e:
                        session.rollback()
                        logger.error("⚠️ Error inserting bar for %s: %s", symbol, inner_e)

                if new_rows:
                    with open(outfile, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerows(new_rows)

                    logger.info("✓ Logged %s new bars for %s", len(new_rows), symbol)
                else:
                    logger.info("No new unique bars")

        except Exception as e:  # noqa: BLE001
            logger.error("❌ Error during ingestion: %s", e)

        time.sleep(interval)


if __name__ == "__main__":
    run_polygon_ingestor(interval=30, symbol="AAPL")
