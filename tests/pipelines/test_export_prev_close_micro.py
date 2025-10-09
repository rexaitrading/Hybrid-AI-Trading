import os
import json
import csv
import pytest
from pathlib import Path

import hybrid_ai_trading.pipelines.export_prev_close as mod
from hybrid_ai_trading.data.clients.polygon_client import PolygonAPIError


def test_safe_export_header_only_hits_line_50(tmp_path, caplog):
    """Call _safe_export with empty rows for CSV and JSON to hit header-only/success log."""
    caplog.set_level("INFO")
    # CSV with empty rows
    csv_path = tmp_path / "empty.csv"
    mod.DATA_DIR = str(tmp_path)  # write under tmp
    mod._safe_export(str(csv_path), [], mode="csv")
    assert csv_path.exists()
    # JSON with empty rows
    json_path = tmp_path / "empty.json"
    mod._safe_export(str(json_path), [], mode="json")
    assert json_path.exists()
    # success log present
    assert "Exported" in caplog.text


@pytest.mark.parametrize("crypto_ret, stocks, expect_files", [
    # Polygon constructor fails (PolygonAPIError) -> warn branch hits, no rows -> no files
    ({}, [], False),
])
def test_polygon_constructor_unavailable_warn_and_all_rows_false(monkeypatch, tmp_path, caplog, crypto_ret, stocks, expect_files):
    """
    - Force PolygonClient() to raise PolygonAPIError -> except warning branch.
    - batch_prev_close returns {} so crypto contributes no rows.
    - Core_Stocks empty -> all_rows remains empty -> skip export but exit 0.
    """
    caplog.set_level("WARNING")
    # point writes under tmp
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "DATA_DIR", "data")

    # No crypto rows
    monkeypatch.setattr(mod, "batch_prev_close", lambda *_a, **_k: crypto_ret)

    # Ensure PolygonClient constructor raises PolygonAPIError
    monkeypatch.setattr(mod, "PolygonClient", lambda *a, **k: (_ for _ in ()).throw(PolygonAPIError("no key")))

    # Make Core_Stocks empty so we definitely have all_rows == []
    monkeypatch.setattr(mod, "Core_Stocks", [])

    # Patch sys.exit so tests don't abort
    monkeypatch.setattr(mod.sys, "exit", lambda code=0: None)

    # Run
    mod.main()

    # Warning branch was hit
    assert "PolygonClient unavailable" in caplog.text

    # Since all_rows is empty, no export files should exist
    data_dir = Path("data")
    if data_dir.exists():
        files = list(data_dir.glob("*"))
        assert (len(files) == 0) == (not expect_files)
