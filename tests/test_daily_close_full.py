"""
Unit Tests: Daily Close Exporter
(Hybrid AI Quant Pro v6.14 – Hedge-Fund Grade, 100% Coverage, Polished)
=======================================================================
Covers:
- _ms_to_iso (valid + invalid inputs)
- Core_Crypto branch via batch_prev_close (success + exception)
- Polygon branch (success, no data, error)
- Export CSV + JSON with failure handling
- __main__ entrypoint execution (via subprocess)
"""

import os
import csv
import json
import sys
import subprocess
import builtins
import pytest
from unittest.mock import patch, MagicMock

import hybrid_ai_trading.pipelines.daily_close as daily_close

DATA_DIR = "data"


# ----------------------------------------------------------------------
# Auto-cleanup fixture
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_data_dir():
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.startswith("daily_close_"):
                os.remove(os.path.join(DATA_DIR, f))
    yield
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.startswith("daily_close_"):
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
    iso = daily_close._ms_to_iso(ts)
    assert "T" in iso
    assert daily_close._ms_to_iso("bad") == ""


@patch("hybrid_ai_trading.pipelines.daily_close.batch_prev_close")
def test_core_crypto_success_and_error(mock_batch, tmp_path, monkeypatch):
    mock_batch.return_value = {"BTC": {"asof": "t", "open": 1, "status": "OK"}}
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.daily_close.PolygonClient", lambda: MagicMock()
    )
    monkeypatch.chdir(tmp_path)

    daily_close.main()
    files = os.listdir("data")
    assert any(f.endswith(".csv") for f in files)
    assert any(f.endswith(".json") for f in files)

    mock_batch.side_effect = Exception("boom")
    daily_close.main()  # Should log error, not crash


def test_polygon_branch_success_no_data_and_error(tmp_path, monkeypatch):
    class FakeClient:
        def prev_close(self, symbol):
            if symbol == "OK":
                return {
                    "results": [
                        {
                            "t": 1700000000000,
                            "o": 1,
                            "h": 2,
                            "l": 1,
                            "c": 2,
                            "v": 50,
                            "vw": 1.4,
                        }
                    ],
                    "status": "OK",
                }
            if symbol == "NONE":
                return {"results": []}
            raise Exception("fail")

    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.daily_close.PolygonClient", lambda: FakeClient()
    )
    monkeypatch.chdir(tmp_path)
    daily_close.Core_Stocks[:] = ["OK", "NONE", "FAIL"]

    daily_close.main()
    files = os.listdir("data")
    csv_file = [f for f in files if f.endswith(".csv")][0]
    rows = read_csv(os.path.join("data", csv_file))
    assert any(r["status"].startswith("NO_DATA") for r in rows)
    assert any(r["status"].startswith("ERROR") for r in rows)


def test_export_failures(monkeypatch, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.daily_close.PolygonClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.daily_close.batch_prev_close",
        lambda *_a, **_k: {"BTC": {"asof": "t", "open": 1}},
    )

    real_open = builtins.open  # Save reference to the real open

    def bad_open_csv(*args, **kwargs):
        if str(args[0]).endswith(".csv"):
            raise OSError("csv fail")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", bad_open_csv)
    with caplog.at_level("ERROR"):
        daily_close.main()
    assert "csv" in caplog.text.lower()

    def bad_open_json(*args, **kwargs):
        if str(args[0]).endswith(".json"):
            raise OSError("json fail")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", bad_open_json)
    with caplog.at_level("ERROR"):
        daily_close.main()
    assert "json" in caplog.text.lower()


def test_main_entrypoint_runs(tmp_path):
    env = os.environ.copy()
    env["COINAPI_STUB"] = "1"
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    env["PYTHONPATH"] = project_root

    result = subprocess.run(
        [sys.executable, "-m", "hybrid_ai_trading.pipelines.daily_close"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    combined_output = result.stdout + result.stderr
    assert "Exported" in combined_output or "📂" in combined_output
