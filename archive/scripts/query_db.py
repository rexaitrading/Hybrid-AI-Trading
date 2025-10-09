"""
Event → Price Impact Dataset Builder (Quant Pro v5.6)
-----------------------------------------------------
- Pull headlines from DB (all by default, or N if specified)
- Match with prices (same-day or prev trading day)
- Compute same-day + next-day returns
- Export joined dataset to CSV + SQLite (event_price_impact)
"""

import csv
import os

from sqlalchemy import func

from hybrid_ai_trading.data.store.database import (Base, News, Price,
                                                   SessionLocal, engine)


def query_news_with_prices(limit=None, symbol="AAPL", export_csv=True, export_db=True):
    session = SessionLocal()

    print(
        f"\n=== Building Event-Driven Dataset (limit={limit or 'ALL'}, symbol={symbol}) ==="
    )

    # Pull headlines
    headlines_query = session.query(News).order_by(News.created.desc())
    if limit:
        headlines_query = headlines_query.limit(limit)
    headlines = headlines_query.all()

    results = []

    for n in headlines:
        news_date = n.created.date()

        # Same-day price
        price_today = (
            session.query(Price)
            .filter(Price.symbol == symbol, func.date(Price.timestamp) == news_date)
            .first()
        )

        # Fallback: previous trading day
        fallback = ""
        if not price_today:
            price_today = (
                session.query(Price)
                .filter(Price.symbol == symbol, func.date(Price.timestamp) < news_date)
                .order_by(Price.timestamp.desc())
                .first()
            )
            fallback = " (prev trading day)" if price_today else ""

        # Next-day price
        price_next = (
            session.query(Price)
            .filter(Price.symbol == symbol, func.date(Price.timestamp) > news_date)
            .order_by(Price.timestamp.asc())
            .first()
        )

        same_day_return = (
            (price_today.close - price_today.open) / price_today.open * 100
            if price_today and price_today.open
            else None
        )

        next_day_return = (
            (price_next.close - price_next.open) / price_next.open * 100
            if price_next and price_next.open
            else None
        )

        results.append(
            {
                "headline_time": n.created,
                "headline": n.title,
                "price_date": price_today.timestamp.date() if price_today else None,
                "fallback": fallback,
                "open": price_today.open if price_today else None,
                "close": price_today.close if price_today else None,
                "same_day_return_pct": same_day_return,
                "next_day_date": price_next.timestamp.date() if price_next else None,
                "next_day_return_pct": next_day_return,
            }
        )

    # -------------------------
    # Export to CSV
    # -------------------------
    if export_csv and results:
        os.makedirs("reports", exist_ok=True)
        csv_path = "reports/news_price_impact.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"📂 Exported CSV → {csv_path}")

    # -------------------------
    # Export to SQLite table
    # -------------------------
    if export_db and results:
        from sqlalchemy import (Column, DateTime, Float, Integer, MetaData,
                                String, Table)

        metadata = Base.metadata
        event_table = Table(
            "event_price_impact",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("headline_time", DateTime),
            Column("headline", String),
            Column("price_date", String),
            Column("fallback", String),
            Column("open", Float),
            Column("close", Float),
            Column("same_day_return_pct", Float),
            Column("next_day_date", String),
            Column("next_day_return_pct", Float),
            extend_existing=True,
        )
        metadata.create_all(engine)

        with engine.begin() as conn:
            conn.execute(event_table.delete())  # clear old data
            conn.execute(event_table.insert(), results)

        print("🗄️ Exported to SQLite table → event_price_impact")

    if not results:
        print("⚠️ No results found (check if headlines & prices overlap in time)")

    session.close()


if __name__ == "__main__":
    # Default: pull ALL headlines
    query_news_with_prices(limit=None, symbol="AAPL")
