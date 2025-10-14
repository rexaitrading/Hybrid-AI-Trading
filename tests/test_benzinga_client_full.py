import os
import pytest
from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient, BenzingaAPIError

@pytest.fixture(autouse=True)
def clear_benzinga_env(monkeypatch):
    # Make this module immune to suite-wide env or dotenv loaders
    for k in ("BENZINGA_KEY", "BENZINGA_API_KEY"):
        monkeypatch.delenv(k, raising=False)

def test_init_with_env_and_missing(monkeypatch):
    """Init: picks up env key or raises if missing."""
    # Case 1: BENZINGA_KEY present -> client should use it
    monkeypatch.setenv("BENZINGA_KEY", "FAKEKEY")
    client = BenzingaClient()
    assert client.api_key == "FAKEKEY"

    # Case 2: No env keys -> should raise
    monkeypatch.delenv("BENZINGA_KEY", raising=False)
    monkeypatch.delenv("BENZINGA_API_KEY", raising=False)
    with pytest.raises(BenzingaAPIError):
        BenzingaClient()
