"""
Unit Tests: Export Leaderboard (Hybrid AI Quant Pro – Hedge-Fund Grade, 100% Coverage)
--------------------------------------------------------------------------------------
Covers export_leaderboard behavior in all branches:
- Normal data export
- Empty DataFrame (headers only)
- Exception handling (force failure with monkeypatch)
"""

import pandas as pd
import pytest

from hybrid_ai_trading.execution.leaderboard import export_leaderboard


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def sample_df():
    """Fixture: sample leaderboard DataFrame."""
    return pd.DataFrame(
        {
            "strategy": ["VWAP", "TWAP", "Kelly"],
            "sharpe": [1.5, 1.2, 2.0],
            "sortino": [2.2, 1.8, 2.5],
        }
    )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_export_leaderboard_success(sample_df, tmp_path):
    """✅ Should export leaderboard DataFrame to CSV with correct shape and headers."""
    out_file = tmp_path / "leaderboard.csv"
    export_leaderboard(sample_df, out_file)

    # Reload to verify contents
    loaded = pd.read_csv(out_file)
    assert not loaded.empty
    assert list(loaded.columns) == list(sample_df.columns)
    assert loaded.shape == sample_df.shape


def test_export_leaderboard_empty(tmp_path):
    """⚠️ Should export headers only when DataFrame is empty."""
    df = pd.DataFrame(columns=["strategy", "sharpe", "sortino"])
    out_file = tmp_path / "empty.csv"
    export_leaderboard(df, out_file)

    loaded = pd.read_csv(out_file)
    # DataFrame should load with headers but no rows
    assert loaded.empty
    assert list(loaded.columns) == ["strategy", "sharpe", "sortino"]


def test_export_leaderboard_error(monkeypatch, sample_df, tmp_path, caplog):
    """❌ Should log error and cleanup file when export fails."""
    caplog.set_level("ERROR")

    # Force pandas to raise an error
    monkeypatch.setattr(
        pd.DataFrame,
        "to_csv",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")),
    )

    out_file = tmp_path / "fail.csv"
    export_leaderboard(sample_df, out_file)

    # File should not exist
    assert not out_file.exists()
    assert "boom" in caplog.text.lower()
