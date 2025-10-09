"""
Backfill Sentiment Scores into News Table (Quant Pro v6.4 – Polished)
---------------------------------------------------------------------
Responsibilities:
- Ensure `sentiment_score` column exists in the news table
- Read headlines from SQLite DB
- Run sentiment analysis (VADER or FinBERT, per config.yaml)
- Store scores into `sentiment_score`
- Always print summary output, even if no rows were updated
"""

import logging
from typing import Optional

import yaml
from sqlalchemy import text

from hybrid_ai_trading.data.store.database import News, SessionLocal
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter

# ==========================================================
# Logging
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("BackfillSentiment")

# ==========================================================
# Load Config
# ==========================================================
with open("config/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

sent_cfg = cfg.get("sentiment", {})
MODEL: str = sent_cfg.get("model", "vader")
THRESHOLD: float = float(sent_cfg.get("threshold", 0.8))

# ==========================================================
# Sentiment Analyzer & DB Session
# ==========================================================
sent_filter = SentimentFilter(enabled=True, model=MODEL, threshold=THRESHOLD)
session = SessionLocal()


# ==========================================================
# Helpers
# ==========================================================
def add_sentiment_column() -> None:
    """Ensure `sentiment_score` column exists in the `news` table."""
    with session.bind.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE news ADD COLUMN sentiment_score FLOAT"))
            logger.info("✅ Added sentiment_score column to news table")
        except Exception as e:  # noqa: BLE001
            if "duplicate column" in str(e).lower():
                logger.info("ℹ️ sentiment_score column already exists")
            else:
                logger.error("❌ Error adding column: %s", e)


def backfill_sentiment(limit: int = 5000) -> None:
    """Process headlines and populate sentiment scores."""
    headlines = (
        session.query(News).filter(News.sentiment_score.is_(None)).limit(limit).all()
    )

    if not headlines:
        logger.info("ℹ️ No new headlines found without sentiment_score")
        return

    logger.info("🔎 Processing %d headlines with model=%s", len(headlines), MODEL)

    updated = 0
    for headline in headlines:
        try:
            text_to_score: str = headline.title or ""
            score: Optional[float] = sent_filter.score(text_to_score)
            headline.sentiment_score = score
            session.add(headline)
            updated += 1
        except Exception as e:  # noqa: BLE001
            logger.error(
                "❌ Error scoring headline %s: %s",
                getattr(headline, "id", "?"),
                e,
            )

    session.commit()
    logger.info("✅ Backfilled %d headlines with sentiment scores", updated)


# ==========================================================
# Entrypoint
# ==========================================================
if __name__ == "__main__":
    print("🚀 Starting sentiment backfill...")
    add_sentiment_column()
    backfill_sentiment()
    print("🏁 Sentiment backfill finished.")
