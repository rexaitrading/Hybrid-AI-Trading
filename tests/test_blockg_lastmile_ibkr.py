from __future__ import annotations

from pathlib import Path

import pytest


def _write_no_bom(path: Path, text: str) -> None:
    # encode("utf-8") => NO BOM
    path.write_bytes(text.encode("utf-8"))


def test_ib_adapter_lastmile_blocks_nvda_when_contract_false(tmp_path, monkeypatch):
    contract = tmp_path / "blockg_false.json"
    _write_no_bom(contract, '{"as_of_date":"2025-12-11","nvda_blockg_ready":false}')

    monkeypatch.setenv("BLOCKG_CONTRACT_PATH", str(contract))

    # Import after env set so reader sees override
    from hybrid_ai_trading.brokers.ib_adapter import IBAdapter

    a = IBAdapter()
    a.ib = None  # ensure we never reach IB calls

    with pytest.raises(RuntimeError) as exc:
        a.place_order("NVDA", "BUY", 1)

    msg = str(exc.value)
    assert "[BLOCK-G]" in msg
    assert "NVDA" in msg


def test_ib_adapter_lastmile_allows_non_nvda_even_if_contract_false(tmp_path, monkeypatch):
    contract = tmp_path / "blockg_false.json"
    _write_no_bom(contract, '{"as_of_date":"2025-12-11","nvda_blockg_ready":false}')

    monkeypatch.setenv("BLOCKG_CONTRACT_PATH", str(contract))

    from hybrid_ai_trading.brokers.ib_adapter import IBAdapter

    a = IBAdapter()
    a.ib = None

    # For non-NVDA, Block-G should NOT trigger; failure should be downstream (a.ib=None)
    with pytest.raises(Exception) as exc:
        a.place_order("AAPL", "BUY", 1)

    assert "[BLOCK-G]" not in str(exc.value)