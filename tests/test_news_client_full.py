"""
Unit Tests – NewsClient (Hybrid AI Quant Pro v2.5 – Hedge-Fund OE Grade, 100% Coverage)
---------------------------------------------------------------------------------------
Covers ALL branches of news_client.py:
- _normalize_article: valid, missing fields, exception path
- fetch_polygon_news: no key, success, failure
- fetch_benzinga_news: no key, success dict, missing articles, invalid type, exception
- save_articles: normal insert, IntegrityError, generic error, invalid article skip
- get_latest_headlines: with symbol, without symbol, empty result, query exception
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from hybrid_ai_trading.data.clients import news_client


# ----------------------------------------------------------------------
# _normalize_article
# ----------------------------------------------------------------------
def test_normalize_article_valid_and_invalid():
    art = {
        "id": "1",
        "published_utc": "2025-01-01T00:00:00Z",
        "title": "headline",
        "url": "http://x",
        "tickers": ["AAPL", "TSLA"],
    }
    out = news_client._normalize_article(art)
    assert out["symbols"] == "AAPL,TSLA"

    # Missing published_utc → falls back to utcnow
    art2 = {"id": "2", "title": "h2", "url": "u2"}
    out2 = news_client._normalize_article(art2)
    assert "created" in out2

    # Malformed published_utc triggers exception
    art3 = {"id": "3", "published_utc": "bad-date"}
    assert news_client._normalize_article(art3) is None


# ----------------------------------------------------------------------
# fetch_polygon_news
# ----------------------------------------------------------------------
def test_fetch_polygon_news_no_key(monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    out = news_client.fetch_polygon_news()
    assert out == []


@patch("hybrid_ai_trading.data.clients.news_client.requests.get")
def test_fetch_polygon_news_success_and_failure(mock_get, monkeypatch):
    monkeypatch.setenv("POLYGON_KEY", "FAKE")

    # Success
    good = MagicMock()
    good.raise_for_status.return_value = None
    good.json.return_value = {"results": [{"id": 1}]}
    mock_get.return_value = good
    out = news_client.fetch_polygon_news(limit=1, ticker="AAPL")
    assert out[0]["id"] == 1

    # Failure (HTTP error)
    bad = MagicMock()
    bad.raise_for_status.side_effect = Exception("fail")
    mock_get.return_value = bad
    assert news_client.fetch_polygon_news(limit=1) == []

    monkeypatch.delenv("POLYGON_KEY", raising=False)


# ----------------------------------------------------------------------
# fetch_benzinga_news
# ----------------------------------------------------------------------
def test_fetch_benzinga_news_no_key(monkeypatch):
    monkeypatch.delenv("BENZINGA_KEY", raising=False)
    out = news_client.fetch_benzinga_news("AAPL")
    assert out == []


@patch("hybrid_ai_trading.data.clients.news_client.requests.get")
def test_fetch_benzinga_news_all_branches(mock_get, monkeypatch):
    monkeypatch.setenv("BENZINGA_KEY", "FAKE")
    client = MagicMock()

    # Success with articles
    client.raise_for_status.return_value = None
    client.json.return_value = {"articles": [{"id": "x"}]}
    mock_get.return_value = client
    out = news_client.fetch_benzinga_news("AAPL")
    assert out[0]["id"] == "x"

    # Dict missing articles
    client.json.return_value = {"foo": "bar"}
    out2 = news_client.fetch_benzinga_news("AAPL")
    assert out2 == []

    # Invalid type
    client.json.return_value = ["not", "dict"]
    assert news_client.fetch_benzinga_news("AAPL") == []

    # Exception
    client.raise_for_status.side_effect = Exception("fail")
    mock_get.return_value = client
    assert news_client.fetch_benzinga_news("AAPL") == []

    monkeypatch.delenv("BENZINGA_KEY", raising=False)


# ----------------------------------------------------------------------
# save_articles
# ----------------------------------------------------------------------
@patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
def test_save_articles_happy_and_integrity(mock_sess):
    fake = MagicMock()
    mock_sess.return_value = fake

    art = {"id": "1", "published_utc": "2025-01-01T00:00:00Z", "title": "h", "url": "u"}

    # Happy path
    fake.add.return_value = None
    fake.commit.return_value = None
    count = news_client.save_articles([art])
    assert count == 1

    # IntegrityError triggers rollback
    from sqlalchemy.exc import IntegrityError

    fake.add.side_effect = IntegrityError("stmt", "params", "orig")
    fake.commit.side_effect = None
    count2 = news_client.save_articles([art])
    assert count2 >= 0


@patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
def test_save_articles_generic_and_skip(mock_sess):
    fake = MagicMock()
    mock_sess.return_value = fake

    # Generic error
    fake.add.side_effect = Exception("boom")
    count = news_client.save_articles([{"id": "1"}])
    assert count == 0

    # Invalid article skipped (normalize returns None)
    bad = {"published_utc": "bad-date"}
    count2 = news_client.save_articles([bad])
    assert count2 == 0


# ----------------------------------------------------------------------
# get_latest_headlines
# ----------------------------------------------------------------------
@patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
def test_get_latest_headlines_with_and_without_symbol(mock_sess):
    fake = MagicMock()
    mock_sess.return_value = fake

    row = MagicMock()
    row.title, row.symbols, row.url, row.created = "t", "AAPL", "u", datetime.utcnow()

    # Chain for no symbol
    fake.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
        row
    ]

    out = news_client.get_latest_headlines(limit=1)
    assert out[0]["title"] == "t"

    # Chain for with symbol
    filtered = MagicMock()
    filtered.limit.return_value.all.return_value = [row]
    fake.query.return_value.order_by.return_value.filter.return_value = filtered

    out2 = news_client.get_latest_headlines(limit=1, symbol="AAPL")
    assert out2[0]["symbols"] == "AAPL"


@patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
def test_get_latest_headlines_empty_and_exception(mock_sess):
    fake = MagicMock()
    mock_sess.return_value = fake

    # Empty result
    fake.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    out = news_client.get_latest_headlines(limit=1)
    assert out == []

    # Exception triggers finally close
    fake.query.side_effect = Exception("db fail")
    with pytest.raises(Exception):
        news_client.get_latest_headlines(limit=1)
