"""
Backfill sentiment scores into news table (Quant Pro v6.3.1)
------------------------------------------------------------
Responsibilities:
- Ensure `sentiment_score` column exists in the news table
- Read headlines from SQLite DB
- Run sentiment analysis (VADER or FinBERT, per config.yaml)
- Store scores into `sentiment_score`
- Always print summary output, even if no rows were updated
"""

import logging
import yaml
from sqlalchemy import text
from hybrid_ai_trading.data.store.database import SessionLocal, News
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("BackfillSentiment")

# --- Load config.yaml ---
with open("config/config.yaml", "r", encoding="utf-8-sig") as f:
    cfg = yaml.safe_load(f)

sent_cfg = cfg.get("sentiment", {})
model = sent_cfg.get("model", "vader")
threshold = float(sent_cfg.get("threshold", 0.8))

# --- Sentiment Analyzer ---
sent_filter = SentimentFilter(enabled=True, model=model, threshold=threshold)

# --- DB Session ---
session = SessionLocal()


def add_sentiment_column():
    """Ensure sentiment_score column exists in news table."""
    with session.bind.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE news ADD COLUMN sentiment_score FLOAT"))
            logger.info("✅ Added sentiment_score column to news table")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.info("ℹ️ sentiment_score column already exists")
            else:
                logger.error(f"❌ Error adding column: {e}")


def backfill_sentiment(limit=5000):
    """Process headlines and add sentiment scores."""
    headlines = session.query(News).filter(News.sentiment_score == None).limit(limit).all()

    if not headlines:
        print("ℹ️ No new headlines found without sentiment_score")
        return

    print(f"🔎 Processing {len(headlines)} headlines with model={model}")

    for h in headlines:
        try:
            score = sent_filter.score(h.title or "")
            h.sentiment_score = score
            session.add(h)
        except Exception as e:
            logger.error(f"❌ Error scoring headline {h.id}: {e}")

    session.commit()
    print(f"✅ Backfilled {len(headlines)} headlines with sentiment scores")


if __name__ == "__main__":
    print("🚀 Starting sentiment backfill...")
    add_sentiment_column()
    backfill_sentiment()
    print("🏁 Sentiment backfill finished.")
