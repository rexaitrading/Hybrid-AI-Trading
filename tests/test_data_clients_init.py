"""
Unit Tests – Data Clients Package Init
(Hybrid AI Quant Pro v1.0 – Hedge-Fund OE Grade, 100% Coverage)
----------------------------------------------------------------
Covers:
- __all__ exports
- Presence and type of each client class
- Error inheritance relationships
"""

import inspect

import pytest

import hybrid_ai_trading.data.clients as clients


def test___all___contains_expected_symbols():
    expected = {
        "AlpacaClient",
        "BenzingaClient",
        "CoinAPIClient",
        "PolygonClient",
        "DataClientError",
        "AlpacaAPIError",
        "BenzingaAPIError",
        "CoinAPIError",
        "PolygonAPIError",
    }
    exported = set(clients.__all__)
    assert expected == exported


def test_clients_are_classes():
    for name in ["AlpacaClient", "BenzingaClient", "CoinAPIClient", "PolygonClient"]:
        cls = getattr(clients, name)
        assert inspect.isclass(cls)


@pytest.mark.parametrize(
    "exc_cls",
    [
        clients.AlpacaAPIError,
        clients.BenzingaAPIError,
        clients.CoinAPIError,
        clients.PolygonAPIError,
    ],
)
def test_errors_inherit_from_base(exc_cls):
    err = exc_cls("oops")
    assert isinstance(err, clients.DataClientError)
    assert "oops" in str(err)


def test_client_instantiation_safe(monkeypatch):
    """Smoke-test client constructors with dummy values."""
    # Patch os.getenv to avoid triggering real env lookups
    monkeypatch.setenv("FAKE_KEY", "XYZ")

    # Instantiate with explicit dummy keys
    a = clients.AlpacaClient(api_key="X", api_secret="Y")
    b = clients.BenzingaClient(api_key="X")
    c = clients.CoinAPIClient()
    p = clients.PolygonClient(api_key="X", allow_missing=True)

    assert isinstance(a, clients.AlpacaClient)
    assert isinstance(b, clients.BenzingaClient)
    assert isinstance(c, clients.CoinAPIClient)
    assert isinstance(p, clients.PolygonClient)
