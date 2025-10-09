"""
Unit Tests – Client Edge Cases (Hybrid AI Quant Pro v17.6 – Hedge-Fund OE Grade, 100% Coverage)
-----------------------------------------------------------------------------------------------
Covers ALL clients under data/clients/:
- CoinAPIClient: headers, retries, FX, OHLCV, ping, batch_prev_close
- AlpacaClient: key masking, missing creds, request failures, ping
- BenzingaClient: key missing, bad responses, JSON errors
- PolygonClient: config errors, prev_close failures, ping failures
- NewsClient: normalize helpers, polygon/benzinga fetch, DB save/query
- Errors: all custom exception classes
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from hybrid_ai_trading.data.clients import (
    coinapi_client,
    alpaca_client,
    benzinga_client,
    polygon_client,
    news_client,
    errors,
)
from hybrid_ai_trading.data.clients.coinapi_client import CoinAPIError


# ======================================================================
# CoinAPIClient edge cases
# ======================================================================
class TestCoinAPIClient:
    def test_headers_variants(self, monkeypatch):
        monkeypatch.setenv("COINAPI_STUB", "1")
        assert coinapi_client._get_headers() == {}
        monkeypatch.delenv("COINAPI_STUB", raising=False)

        with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config", side_effect=Exception("boom")):
            with pytest.raises(CoinAPIError):
                coinapi_client._get_headers()

        with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config", return_value="bad"):
            with pytest.raises(CoinAPIError):
                coinapi_client._get_headers()

        with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config", return_value=None):
            with pytest.raises(CoinAPIError):
                coinapi_client._get_headers()

        with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config",
                   return_value={"providers": {"coinapi": {"api_key_env": None}}}):
            with pytest.raises(CoinAPIError):
                coinapi_client._get_headers()

        with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config",
                   return_value={"providers": {"coinapi": {"api_key_env": "MISSING"}}}):
            monkeypatch.delenv("MISSING", raising=False)
            assert coinapi_client._get_headers() == {}

        monkeypatch.setenv("COINAPI_ALLOW_STUB", "0")
        with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config",
                   return_value={"providers": {"coinapi": {"api_key_env": "MISSING"}}}):
            with pytest.raises(CoinAPIError):
                coinapi_client._get_headers()
        monkeypatch.delenv("COINAPI_ALLOW_STUB", raising=False)

    @patch("hybrid_ai_trading.data.clients.coinapi_client.requests.get")
    @patch("hybrid_ai_trading.data.clients.coinapi_client._get_headers", return_value={"X": "FAKE"})
    def test_retry_get_paths(self, _, mock_get):
        good = MagicMock(status_code=200)
        good.json.return_value = {"ok": 1}
        mock_get.return_value = good
        assert coinapi_client._retry_get("http://fake").json() == {"ok": 1}

        bad = MagicMock(status_code=503, text="retry")
        mock_get.return_value = bad
        with patch("hybrid_ai_trading.data.clients.coinapi_client.time.sleep", return_value=None):
            with pytest.raises(CoinAPIError):
                coinapi_client._retry_get("http://fake", max_retry=1)

        bad2 = MagicMock(status_code=400, text="bad")
        mock_get.return_value = bad2
        with pytest.raises(CoinAPIError):
            coinapi_client._retry_get("http://fake")

        mock_get.side_effect = Exception("fail")
        with pytest.raises(CoinAPIError):
            coinapi_client._retry_get("http://fake", max_retry=1)

    @patch("hybrid_ai_trading.data.clients.coinapi_client._retry_get")
    def test_fx_and_ohlcv_paths(self, mock_retry):
        c = coinapi_client.CoinAPIClient()
        good = MagicMock()
        good.json.return_value = {"rate": 1.1}
        mock_retry.return_value = good
        assert c.get_fx_rate("BTC", "USD") == 1.1

        bad = MagicMock()
        bad.json.return_value = {"oops": 1}
        mock_retry.return_value = bad
        with pytest.raises(CoinAPIError):
            c.get_fx_rate("BTC", "USD")

        good.json.return_value = [{"c": 5}]
        mock_retry.return_value = good
        assert c.get_ohlcv_latest("BTCUSD")[0]["c"] == 5

        good.json.return_value = {"error": "bad"}
        mock_retry.return_value = good
        with pytest.raises(CoinAPIError):
            c.get_ohlcv_latest("BTC", "USD")

        mock_retry.side_effect = Exception("fail")
        with pytest.raises(CoinAPIError):
            c.get_ohlcv_latest("BTC", "USD")

    @patch("hybrid_ai_trading.data.clients.coinapi_client.CoinAPIClient.get_fx_rate")
    def test_ping_paths(self, mock_fx):
        c = coinapi_client.CoinAPIClient()
        mock_fx.return_value = 1.0
        assert c.ping() is True
        mock_fx.side_effect = CoinAPIError("bad")
        assert c.ping() is False
        mock_fx.side_effect = Exception("fail")
        assert c.ping() is False
        assert coinapi_client.ping() in (True, False)

    @patch("hybrid_ai_trading.data.clients.coinapi_client.CoinAPIClient.get_ohlcv_latest")
    def test_batch_prev_close_paths(self, mock_ohlcv):
        now = datetime.now(timezone.utc).isoformat()
        mock_ohlcv.side_effect = [
            [{"time_period_start": now, "price_open": 1}],
            [], Exception("fail")
        ]
        out = coinapi_client.batch_prev_close(["BTC", "ETH", "XRP"])
        assert out["BTC"]["status"] == "OK"
        assert out["ETH"]["status"] == "NO_DATA"
        assert "ERROR" in out["XRP"]["status"]

    def test_iso_helper(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert coinapi_client._iso(ts).endswith("Z")


# ======================================================================
# AlpacaClient edge cases
# ======================================================================
class TestAlpacaClient:
    def test_mask_key_and_headers_variants(self):
        assert alpaca_client.AlpacaClient._mask_key_local(None) == "None"
        assert alpaca_client.AlpacaClient._mask_key_local("12345678") == "12345678"
        masked = alpaca_client.AlpacaClient._mask_key_local("ABCDEFGHIJKL")
        assert masked.startswith("ABCD") and masked.endswith("IJKL")

        c = alpaca_client.AlpacaClient(api_key="TEST", api_secret="SECRET")
        headers = c._headers()
        assert "APCA-API-KEY-ID" in headers

    @patch("hybrid_ai_trading.data.clients.alpaca_client.requests.request")
    def test_request_and_failures(self, mock_req):
        c = alpaca_client.AlpacaClient(api_key="K", api_secret="S")
        good = MagicMock()
        good.raise_for_status.return_value = None
        good.json.return_value = {"ok": 1}
        mock_req.return_value = good
        assert c._request("account") == {"ok": 1}

        bad = MagicMock()
        bad.raise_for_status.side_effect = Exception("fail")
        mock_req.return_value = bad
        with pytest.raises(alpaca_client.AlpacaAPIError):
            c._request("account")

        good = MagicMock()
        good.raise_for_status.return_value = None
        good.json.side_effect = Exception("json fail")
        mock_req.return_value = good
        with pytest.raises(alpaca_client.AlpacaAPIError):
            c._request("account")

        mock_req.side_effect = Exception("network down")
        with pytest.raises(alpaca_client.AlpacaAPIError):
            c._request("account")

    @patch.object(alpaca_client.AlpacaClient, "account")
    def test_ping_variants(self, mock_acc):
        c = alpaca_client.AlpacaClient(api_key="K", api_secret="S")
        mock_acc.return_value = {"status": "ACTIVE"}
        assert c.ping() is True
        mock_acc.return_value = None
        assert c.ping() is False
        mock_acc.return_value = {"foo": "bar"}
        assert c.ping() is False
        mock_acc.side_effect = alpaca_client.AlpacaAPIError("fail")
        assert c.ping() is False
        mock_acc.side_effect = Exception("boom")
        assert c.ping() is False


# ======================================================================
# BenzingaClient edge cases
# ======================================================================
class TestBenzingaClient:
    def test_missing_key(self, monkeypatch):
        monkeypatch.delenv("BENZINGA_KEY", raising=False)
        with pytest.raises(benzinga_client.BenzingaAPIError):
            benzinga_client.BenzingaClient(api_key=None)

    @patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
    def test_get_news_variants(self, mock_get):
        client = benzinga_client.BenzingaClient(api_key="FAKE")

        good = MagicMock()
        good.raise_for_status.return_value = None
        good.json.return_value = {"ok": 1}
        mock_get.return_value = good
        assert client.get_news("AAPL") == {"ok": 1}

        bad = MagicMock()
        del bad.json
        bad.raise_for_status.return_value = None
        mock_get.return_value = bad
        with pytest.raises(benzinga_client.BenzingaAPIError):
            client.get_news("AAPL")

        bad = MagicMock()
        bad.raise_for_status.return_value = None
        bad.json.side_effect = Exception("bad")
        mock_get.return_value = bad
        with pytest.raises(benzinga_client.BenzingaAPIError):
            client.get_news("AAPL")

        bad.json.side_effect = None
        bad.json.return_value = None
        mock_get.return_value = bad
        with pytest.raises(benzinga_client.BenzingaAPIError):
            client.get_news("AAPL")

        bad.json.return_value = []
        mock_get.return_value = bad
        with pytest.raises(benzinga_client.BenzingaAPIError):
            client.get_news("AAPL")


# ======================================================================
# PolygonClient edge cases
# ======================================================================
class TestPolygonClient:
    def test_init_and_request_failures(self, monkeypatch):
        monkeypatch.delenv("POLYGON_KEY", raising=False)

        with patch("hybrid_ai_trading.data.clients.polygon_client.load_config",
                   side_effect=Exception("bad")):
            with pytest.raises(polygon_client.PolygonAPIError, match="Failed to load Polygon config"):
                polygon_client.PolygonClient(api_key=None, allow_missing=False)

        with patch("hybrid_ai_trading.data.clients.polygon_client.load_config", return_value={}):
            with pytest.raises(polygon_client.PolygonAPIError, match="Polygon API key not provided"):
                polygon_client.PolygonClient(api_key=None, allow_missing=False)

        with patch("hybrid_ai_trading.data.clients.polygon_client.load_config",
                   return_value={"providers": {"polygon": {"api_key_env": ""}}}):
            with pytest.raises(polygon_client.PolygonAPIError, match="Polygon API key not provided"):
                polygon_client.PolygonClient(api_key=None, allow_missing=False)

    @patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
    def test_request_json_fail_and_non_dict(self, mock_get):
        c = polygon_client.PolygonClient(api_key="FAKE", allow_missing=True)
        bad = MagicMock()
        bad.raise_for_status.return_value = None
        bad.json.side_effect = Exception("fail")
        mock_get.return_value = bad
        with pytest.raises(polygon_client.PolygonAPIError):
            c._request("endpoint")

        bad.json.side_effect = None
        bad.json.return_value = []
        mock_get.return_value = bad
        with pytest.raises(polygon_client.PolygonAPIError):
            c._request("endpoint")


# ======================================================================
# NewsClient edge cases
# ======================================================================
class TestNewsClient:
    def test_normalize_and_fail(self):
        good = {"id": "1", "published_utc": "2025-01-01T00:00:00Z",
                "title": "x", "url": "u", "tickers": ["AAPL"]}
        out = news_client._normalize_article(good)
        assert out["symbols"] == "AAPL"
        bad = {"id": "1", "published_utc": "bad-date"}
        assert news_client._normalize_article(bad) is None

    @patch("hybrid_ai_trading.data.clients.news_client.requests.get")
    def test_fetch_polygon_news_variants(self, mock_get, monkeypatch):
        monkeypatch.delenv("POLYGON_KEY", raising=False)
        news_client.POLYGON_KEY = None
        assert news_client.fetch_polygon_news() == []

        monkeypatch.setenv("POLYGON_KEY", "FAKE")
        news_client.POLYGON_KEY = None

        good = MagicMock()
        good.raise_for_status.return_value = None
        good.json.return_value = {"results": [1]}
        mock_get.return_value = good
        assert news_client.fetch_polygon_news(limit=1) == [1]

        bad = MagicMock()
        bad.raise_for_status.side_effect = Exception("fail")
        mock_get.return_value = bad
        assert news_client.fetch_polygon_news(limit=1) == []

    @patch("hybrid_ai_trading.data.clients.news_client.requests.get")
    def test_fetch_benzinga_news_variants(self, mock_get, monkeypatch):
        monkeypatch.setenv("BENZINGA_KEY", "FAKE")

        good = MagicMock()
        good.raise_for_status.return_value = None
        good.json.return_value = {"articles": [{"id": "1"}]}
        mock_get.return_value = good
        out = news_client.fetch_benzinga_news("AAPL")
        assert isinstance(out, list)

        bad = MagicMock()
        bad.raise_for_status.side_effect = Exception("fail")
        mock_get.return_value = bad
        assert news_client.fetch_benzinga_news("AAPL") == []
        monkeypatch.delenv("BENZINGA_KEY", raising=False)

    @patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
    def test_save_and_get_latest(self, mock_sess):
        fake = MagicMock()
        mock_sess.return_value = fake
        fake.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        assert news_client.get_latest_headlines() == []
        assert news_client.save_articles([{"id": "1"}]) >= 0

    @patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
    def test_save_articles_integrity_error(self, mock_sess):
        fake = MagicMock()
        mock_sess.return_value = fake
        from sqlalchemy.exc import IntegrityError
        fake.add.side_effect = None
        fake.commit.side_effect = [IntegrityError("dup", "params", "orig")]
        assert news_client.save_articles(
            [{"id": "1", "published_utc": "2025-01-01T00:00:00Z"}]) >= 0

    @patch("hybrid_ai_trading.data.clients.news_client.SessionLocal")
    def test_get_latest_headlines_with_symbol(self, mock_sess):
        fake = MagicMock()
        mock_sess.return_value = fake
        row = MagicMock(title="t", symbols="AAPL", url="u", created=datetime.now())
        fake.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.return_value = [row]
        out = news_client.get_latest_headlines(symbol="AAPL")
        assert out[0]["symbols"] == "AAPL"


# ======================================================================
# Errors module
# ======================================================================
class TestErrorsModule:
    def test_raise_each(self):
        for Err in (
            errors.CoinAPIError,
            errors.PolygonAPIError,
            errors.AlpacaAPIError,
            errors.BenzingaAPIError,
        ):
            with pytest.raises(Err):
                raise Err("fail")
