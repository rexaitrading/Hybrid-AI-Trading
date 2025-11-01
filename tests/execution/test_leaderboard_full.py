"""
Unit Tests: Leaderboard Exporter
(Hybrid AI Quant Pro v3.4 â€“ Hedge-Fund OE Grade, 100% Coverage)
----------------------------------------------------------------
Covers all branches of export_leaderboard:
- Success path with normal data
- Empty DataFrame â†’ headers only + warning log
- Exception path â†’ error log + cleanup
- Cleanup failure path (unlink itself fails â†’ logs debug warning)
- Error path where no file exists (skip unlink)
"""

from pathlib import Path

import pandas as pd
import pytest

from hybrid_ai_trading.execution.leaderboard import export_leaderboard


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def sample_df():
    """Fixture: sample leaderboard DataFrame with strategy metrics."""
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
def test_export_leaderboard_success(sample_df, tmp_path, caplog):
    """âœ… Should export a valid DataFrame and log success."""
    out_file: Path = tmp_path / "leaderboard.csv"
    caplog.set_level("INFO")

    export_leaderboard(sample_df, out_file)

    loaded = pd.read_csv(out_file)
    assert not loaded.empty
    assert list(loaded.columns) == list(sample_df.columns)
    assert loaded.shape == sample_df.shape
    assert "exported" in caplog.text.lower()


def test_export_leaderboard_empty(tmp_path, caplog):
    """âš ï¸ Empty DataFrame should export headers only and log warning."""
    df = pd.DataFrame(columns=["strategy", "sharpe", "sortino"])
    out_file: Path = tmp_path / "empty.csv"
    caplog.set_level("WARNING")

    export_leaderboard(df, out_file)

    loaded = pd.read_csv(out_file)
    assert loaded.empty
    assert list(loaded.columns) == ["strategy", "sharpe", "sortino"]
    assert "empty leaderboard" in caplog.text.lower()


def test_export_leaderboard_error_cleanup(monkeypatch, sample_df, tmp_path, caplog):
    """âŒ Force error â†’ should log and cleanup half-written file."""
    caplog.set_level("ERROR")

    def bad_to_csv(*a, **k):
        (tmp_path / "fail.csv").write_text("garbage")
        raise Exception("forced fail")

    monkeypatch.setattr(pd.DataFrame, "to_csv", bad_to_csv)

    out_file: Path = tmp_path / "fail.csv"
    export_leaderboard(sample_df, out_file)

    assert not out_file.exists()
    assert "failed" in caplog.text.lower()


def test_export_leaderboard_cleanup_failure(monkeypatch, sample_df, tmp_path, caplog):
    """âš ï¸ Covers branch where cleanup (unlink) itself raises an error."""
    caplog.set_level("DEBUG")

    out_file: Path = tmp_path / "bad.csv"
    out_file.write_text("half written")

    def bad_to_csv(*a, **k):
        raise Exception("write error")

    def bad_unlink(_self):
        raise PermissionError("cannot delete")

    monkeypatch.setattr(pd.DataFrame, "to_csv", bad_to_csv)
    monkeypatch.setattr(Path, "unlink", bad_unlink)

    export_leaderboard(sample_df, out_file)

    assert out_file.exists()
    assert "failed to cleanup" in caplog.text.lower()


def test_export_leaderboard_error_no_file(monkeypatch, sample_df, tmp_path, caplog):
    """âŒ Error occurs but no file exists â†’ logs error, skips unlink."""
    caplog.set_level("ERROR")

    def bad_to_csv(*a, **k):
        raise Exception("early fail")  # simulate failure before writing file

    monkeypatch.setattr(pd.DataFrame, "to_csv", bad_to_csv)

    out_file: Path = tmp_path / "nofile.csv"
    export_leaderboard(sample_df, out_file)

    assert not out_file.exists()
    assert "failed" in caplog.text.lower()
