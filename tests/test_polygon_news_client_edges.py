import pytest
import requests as _requests

from hybrid_ai_trading.data.clients.polygon_news_client import (
    PolygonAPIError,
    PolygonNewsClient,
)


def test_polygon_request_error(monkeypatch):
    monkeypatch.setenv("POLYGON_KEY", "k")

    def boom(*a, **k):
        raise Exception("net")

    monkeypatch.setattr(_requests, "get", boom)
    with pytest.raises(PolygonAPIError):
        PolygonNewsClient().get_news("AAPL", 1, "2025-09-30")
