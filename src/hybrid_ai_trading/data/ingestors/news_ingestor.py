from hybrid_ai_trading.utils.time_utils import utc_now

"""
Benzinga News Ingestor (Quant Pro v6.0)
---------------------------------------
- Fetches live OR historical headlines from Benzinga
- Saves to both CSV + SQLite (news table)
- Supports configurable date ranges for backfilling research data
"""

import csv
import logging
import os
from datetime import datetime, timedelta

from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient
from hybrid_ai_trading.data.store.database import News, SessionLocal, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def ingest_news(
    symbols="AAPL,TSLA,BTCUSD",
    outfile="data/news_feed.csv",
    date_from=None,
    date_to=None,
    limit=50,
):
    """
    Fetch Benzinga headlines and log into CSV + DB.

    Parameters
    ----------
    symbols : str
        Comma-separated tickers.
    outfile : str
        CSV backup file path.
    date_from : str
        Start date (YYYY-MM-DD) for historical fetch.
    date_to : str
        End date (YYYY-MM-DD). Defaults to today.
    limit : int
        Max headlines per API call (Benzinga caps ~100).
    """
    client = BenzingaClient()
    init_db()
    session = SessionLocal()

    os.makedirs(os.path.dirname(outfile), exist_ok=True)

    # Ensure CSV header exists
    if not os.path.exists(outfile):
        with open(outfile, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "created", "title", "url", "symbols"])

    logger.info(f"Ã°Å¸â€Å½ Fetching Benzinga headlines for {symbols}")
    logger.info(f"Date range: {date_from} Ã¢â€ â€™ {date_to or utc_now().date()}")

    # Fetch headlines (API client must support date params)
    articles = client.get_news(
        symbols=symbols, limit=limit, date_from=date_from, date_to=date_to
    )

    if not articles:
        logger.warning("Ã¢Å¡Â Ã¯Â¸Â No articles fetched")
        return

    new_count = 0
    with open(outfile, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for a in articles:
            try:
                created_dt = datetime.strptime(
                    a.get("created"), "%a, %d %b %Y %H:%M:%S %z"
                )
                headline = News(
                    article_id=a.get("id"),
                    created=created_dt,
                    title=a.get("title"),
                    url=a.get("url"),
                    symbols=",".join([s["name"] for s in a.get("stocks", [])]),
                )
                session.add(headline)

                writer.writerow(
                    [
                        a.get("id"),
                        a.get("created"),
                        a.get("title"),
                        a.get("url"),
                        ",".join([s["name"] for s in a.get("stocks", [])]),
                    ]
                )
                new_count += 1
            except Exception as e:
                logger.error(f"Ã¢Å¡Â Ã¯Â¸Â Error saving article: {e}")
                session.rollback()

    session.commit()
    session.close()
    logger.info(f"Ã¢Å“â€œ Logged {new_count} headlines into DB + CSV")


if __name__ == "__main__":
    # Example: Backfill last 60 days
    start_date = (utc_now() - timedelta(days=60)).strftime("%Y-%m-%d")
    ingest_news(symbols="AAPL,TSLA,BTCUSD", date_from=start_date)
