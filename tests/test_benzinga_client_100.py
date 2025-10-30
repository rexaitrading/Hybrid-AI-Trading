import os

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


def test_mask_key_local_variants():
    # Access static util to cover short/long/None branches
    from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient as C

    assert C._mask_key_local(None) == "None"
    assert C._mask_key_local("short7") == "short7"
    assert C._mask_key_local("abcdefgh1234").startswith("abcd") and C._mask_key_local(
        "abcdefgh1234"
    ).endswith("1234")


def test_json_header_but_nonjson_body(monkeypatch):
    os.environ["BENZINGA_API_KEY"] = "k"
    # Content-type says JSON, json() raises, should raise BenzingaAPIError
    monkeypatch.setattr(
        _requests,
        "get",
        lambda *a, **k: R(
            {"content-type": "application/json"}, data=ValueError("badjson")
        ),
    )
    with pytest.raises(BenzingaAPIError):
        BenzingaClient().get_news("AAPL", 1)


def test_text_xml_minimal(monkeypatch):
    os.environ["BENZINGA_API_KEY"] = "k"
    xml = '<?xml version="1.0"?><result is_array="true"><item><id>1</id><author>a</author><created>x</created><updated>y</updated><title>T</title><teaser></teaser><body></body><url>u</url></item></result>'
    monkeypatch.setattr(
        _requests,
        "get",
        lambda *a, **k: R({"content-type": "text/xml"}, data=None, text=xml),
    )
    out = BenzingaClient().get_news("AAPL", 1)
    assert out and out[0]["url"] == "u"
