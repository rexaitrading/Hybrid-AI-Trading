import pytest
import requests as _requests

from hybrid_ai_trading.data.clients.benzinga_client import (
    BenzingaAPIError,
    BenzingaClient,
)


class R:
    def __init__(self, headers, data=None, text=""):
        self._h, self._d, self.text = headers, data, text
        self.status_code = 200

    def raise_for_status(self):
        return None

    @property
    def headers(self):
        return self._h

    def json(self):
        if isinstance(self._d, Exception):
            raise self._d
        return self._d


def test_bz_list_json(monkeypatch):
    monkeypatch.setenv("BENZINGA_API_KEY", "k")
    items = [
        {
            "id": 1,
            "author": "a",
            "created": "c",
            "title": "META beat",
            "url": "u",
            "stocks": [{"name": "META", "exchange": ""}],
        }
    ]
    monkeypatch.setattr(
        _requests, "get", lambda *a, **k: R({"content-type": "application/json"}, items)
    )
    c = BenzingaClient()
    out = c.get_news("META", 1)
    assert out and out[0]["stocks"][0]["name"] == "META"


def test_bz_dict_json_wrap(monkeypatch):
    monkeypatch.setenv("BENZINGA_API_KEY", "k")
    d = {
        "id": 2,
        "author": "a",
        "created": "c",
        "title": "AAPL win",
        "url": "u",
        "stocks": [],
    }
    monkeypatch.setattr(
        _requests, "get", lambda *a, **k: R({"content-type": "application/json"}, d)
    )
    c = BenzingaClient()
    out = c.get_news("AAPL", 1)
    assert isinstance(out, list) and len(out) == 1


def test_bz_json_none_raises(monkeypatch):
    monkeypatch.setenv("BENZINGA_API_KEY", "k")
    monkeypatch.setattr(
        _requests, "get", lambda *a, **k: R({"content-type": "application/json"}, None)
    )
    c = BenzingaClient()

    with pytest.raises(BenzingaAPIError):
        c.get_news("AAPL", 1)


def test_bz_json_fail_raises(monkeypatch):
    monkeypatch.setenv("BENZINGA_API_KEY", "k")
    monkeypatch.setattr(
        _requests,
        "get",
        lambda *a, **k: R({"content-type": "application/json"}, ValueError("bad")),
    )
    c = BenzingaClient()

    with pytest.raises(BenzingaAPIError):
        c.get_news("AAPL", 1)


def test_bz_xml_fallback(monkeypatch):
    monkeypatch.setenv("BENZINGA_API_KEY", "k")
    xml = """<?xml version="1.0"?><result is_array="true"><item>
      <id>9</id><author>bz</author><created>x</created><updated>y</updated>
      <title>TSLA record</title><teaser></teaser><body></body><url>u</url></item></result>"""
    monkeypatch.setattr(
        _requests, "get", lambda *a, **k: R({"content-type": "text/xml"}, None, xml)
    )
    c = BenzingaClient()
    out = c.get_news("TSLA", 1)
    assert out and out[0]["title"].startswith("TSLA")


def test_bz_invalid_type(monkeypatch):
    monkeypatch.setenv("BENZINGA_API_KEY", "k")
    monkeypatch.setattr(
        _requests, "get", lambda *a, **k: R({"content-type": "application/json"}, 123)
    )
    c = BenzingaClient()

    with pytest.raises(BenzingaAPIError):
        c.get_news("AAPL", 1)
