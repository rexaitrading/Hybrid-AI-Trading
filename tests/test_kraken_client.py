import os, json, pytest
from unittest.mock import patch, MagicMock
from hybrid_ai_trading.data.clients.kraken_client import load_client, _resolve_keyfile

def make_temp_keyfile(tmp_path, key="K123", secret="S123"):
    cfg = tmp_path / "kraken_api.json"
    cfg.write_text(json.dumps({"key": key, "secret": secret}))
    return str(cfg)

def test_resolve_with_env(tmp_path, monkeypatch):
    f = make_temp_keyfile(tmp_path)
    monkeypatch.setenv("KRAKEN_KEYFILE", f)
    assert _resolve_keyfile(None) == os.path.abspath(f)

def test_resolve_with_explicit(tmp_path):
    f = make_temp_keyfile(tmp_path)
    assert _resolve_keyfile(f) == os.path.abspath(f)

def test_resolve_missing(monkeypatch):
    monkeypatch.delenv("KRAKEN_KEYFILE", raising=False)
    with pytest.raises(FileNotFoundError):
        _resolve_keyfile("doesnotexist.json")

def test_load_client_reads_json(tmp_path, monkeypatch):
    f = make_temp_keyfile(tmp_path, "AKEY", "ASECRET")
    monkeypatch.setenv("KRAKEN_KEYFILE", f)
    with patch("ccxt.kraken") as mock_kraken:
        mock = MagicMock()
        mock_kraken.return_value = mock
        client = load_client()
        assert client is mock
        mock_kraken.assert_called_once_with({"apiKey": "AKEY", "secret": "ASECRET"})

def test_empty_file_raises(tmp_path, monkeypatch):
    f = tmp_path / "kraken_api.json"
    f.write_text("")
    monkeypatch.setenv("KRAKEN_KEYFILE", str(f))
    with pytest.raises(ValueError):
        load_client()

def test_missing_fields_raises(tmp_path, monkeypatch):
    f = tmp_path / "kraken_api.json"
    f.write_text(json.dumps({"key": "only"}))
    monkeypatch.setenv("KRAKEN_KEYFILE", str(f))
    with pytest.raises(ValueError):
        load_client()
