"""
Unit Tests: Export Previous Close
(Hybrid AI Quant Pro v6.15 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“ Hedge-Fund Grade, 100% Coverage, Polished)
=======================================================================
Covers:
- _ms_to_iso (valid + invalid)
- Core_Crypto branch via batch_prev_close (success + exception)
- Polygon branch (success with data, no data, error)
- Export CSV + JSON with failure handling
- __main__ entrypoint execution (with stub + Polygon missing ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ warning)
"""

import builtins
import csv
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

import hybrid_ai_trading.pipelines.export_prev_close as export_prev_close

DATA_DIR = "data"


# ----------------------------------------------------------------------
# Auto-cleanup fixture
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_data_dir():
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.startswith("prev_close_"):
                os.remove(os.path.join(DATA_DIR, f))
    yield
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.startswith("prev_close_"):
                os.remove(os.path.join(DATA_DIR, f))


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def read_csv(path: str):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_ms_to_iso_valid_and_invalid():
    ts = 1_700_000_000_000
    iso = export_prev_close._ms_to_iso(ts)
    assert "T" in iso
    assert export_prev_close._ms_to_iso("bad") == ""


@patch("hybrid_ai_trading.pipelines.export_prev_close.batch_prev_close")
@patch(
    "sys.exit"
)  # ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ patch sys.exit so tests donÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢t abort
def test_core_crypto_success_and_error(mock_exit, mock_batch, tmp_path, monkeypatch):
    mock_exit.side_effect = lambda code=0: None  # no-op
    mock_batch.return_value = {"BTC/USDT": {"asof": "t", "open": 1, "status": "OK"}}
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.export_prev_close.PolygonClient",
        lambda *a, **k: MagicMock(),
    )
    monkeypatch.chdir(tmp_path)

    export_prev_close.main()
    files = os.listdir("data")
    assert any(f.endswith(".csv") for f in files)
    assert any(f.endswith(".json") for f in files)

    mock_batch.side_effect = Exception("boom")
    export_prev_close.main()  # Should log error, not crash


@patch(
    "hybrid_ai_trading.pipelines.export_prev_close.batch_prev_close", return_value={}
)
@patch("sys.exit")
def test_polygon_branch_success_no_data_and_error(mock_exit, _, tmp_path, monkeypatch):
    mock_exit.side_effect = lambda code=0: None  # no-op

    class FakeClient:
        def prev_close(self, symbol):
            if symbol == "GOOD":
                return {
                    "results": [
                        {
                            "t": 1700000000000,
                            "o": 1,
                            "h": 2,
                            "l": 1,
                            "c": 2,
                            "v": 100,
                            "vw": 1.5,
                        }
                    ],
                    "status": "OK",
                }
            if symbol == "EMPTY":
                return {"results": []}
            raise Exception("api fail")

    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.export_prev_close.PolygonClient",
        lambda *a, **k: FakeClient(),
    )
    monkeypatch.chdir(tmp_path)

    export_prev_close.Core_Stocks[:] = ["GOOD", "EMPTY", "BAD"]
    export_prev_close.main()

    files = os.listdir("data")
    csv_file = [f for f in files if f.endswith(".csv")][0]
    rows = read_csv(os.path.join("data", csv_file))
    assert any(r["status"].startswith("NO_DATA") for r in rows)
    assert any(r["status"].startswith("ERROR") for r in rows)


@patch("sys.exit")
def test_export_failures(mock_exit, monkeypatch, tmp_path, caplog):
    mock_exit.side_effect = lambda code=0: None  # no-op
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.export_prev_close.PolygonClient",
        lambda *a, **k: MagicMock(),
    )
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.export_prev_close.batch_prev_close",
        lambda *_a, **_k: {"BTC": {"asof": "t", "open": 1}},
    )

    def bad_open_csv(*_a, **_k):
        if str(_a[0]).endswith(".csv"):
            raise OSError("csv fail")
        return builtins.open(*_a, **_k)

    monkeypatch.setattr("builtins.open", bad_open_csv)
    with caplog.at_level("ERROR"):
        export_prev_close.main()
    assert "csv" in caplog.text.lower()

    def bad_open_json(*_a, **_k):
        if str(_a[0]).endswith(".json"):
            raise OSError("json fail")
        return builtins.open(*_a, **_k)

    monkeypatch.setattr("builtins.open", bad_open_json)
    with caplog.at_level("ERROR"):
        export_prev_close.main()
    assert "json" in caplog.text.lower()


def test_main_entrypoint_runs(tmp_path):
    """Integration test: run as module with COINAPI_STUB but no POLYGON_KEY ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ should warn, not crash."""
    env = os.environ.copy()
    env["COINAPI_STUB"] = "1"  # stub crypto
    env.pop("POLYGON_KEY", None)  # ensure no Polygon key
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src")
    )
    env["PYTHONPATH"] = project_root

    result = subprocess.run(
        [sys.executable, "-m", "hybrid_ai_trading.pipelines.export_prev_close"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    combined_output = result.stdout + result.stderr
    assert (
        "Exported" in combined_output
        or "ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã¢â‚¬Å¡" in combined_output
        or "PolygonClient unavailable" in combined_output
    )
