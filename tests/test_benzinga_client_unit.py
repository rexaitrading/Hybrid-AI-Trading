import os, types
import pytest

from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient
import requests as _requests

class DummyResp:
    def __init__(self, headers, json_data=None, text_data=""):
        self._headers = headers
        self._json = json_data
        self.text = text_data
        self.status_code = 200
    def raise_for_status(self): return None
    @property
    def headers(self): return self._headers
    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

def test_benzinga_json_and_xml(monkeypatch):
    # Env key
    monkeypatch.setenv("BENZINGA_API_KEY", "bz_test_key")

    # JSON path
    def fake_get_json(url, params=None, headers=None, timeout=15):
        items = [{
            "id": 123, "author":"bz", "created":"Wed, 01 Oct 2025 19:30:00 -0400",
            "title":"META upgrades outlook", "url":"https://example.com/m1",
            "stocks":[{"name":"META","exchange":""}]
        }]
        return DummyResp({"content-type":"application/json"}, json_data=items)

    # XML path
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <result is_array="true">
      <item>
        <id>456</id><author>bz</author>
        <created>Wed, 01 Oct 2025 19:31:00 -0400</created>
        <updated>Wed, 01 Oct 2025 19:31:30 -0400</updated>
        <title>AAPL record profit</title>
        <teaser></teaser><body></body>
        <url>https://example.com/a1</url>
      </item>
    </result>"""
    def fake_get_xml(url, params=None, headers=None, timeout=15):
        return DummyResp({"content-type":"text/xml"}, json_data=None, text_data=xml_text)

    # Patch requests.get to JSON then XML
    calls = {"n":0}
    def switcher(url, params=None, headers=None, timeout=15):
        calls["n"] += 1
        return fake_get_json(url, params, headers, timeout) if calls["n"] == 1 else fake_get_xml(url, params, headers, timeout)
    monkeypatch.setattr(_requests, "get", switcher)

    c = BenzingaClient()
    out1 = c.get_news("META", limit=1)
    assert isinstance(out1, list) and out1[0]["title"].lower().startswith("meta")
    out2 = c.get_news("AAPL", limit=1)
    assert out2[0]["title"].startswith("AAPL")