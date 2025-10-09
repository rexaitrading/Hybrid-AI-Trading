import pandas as pd

from hybrid_ai_trading.execution import leaderboard


def test_export_leaderboard_cleanup(tmp_path, caplog):
    """Covers cleanup branch when export fails."""
    caplog.set_level("ERROR")
    out_file = tmp_path / "bad.csv"

    # Make DataFrame valid but monkeypatch to_csv to fail
    df = pd.DataFrame({"x": [1, 2, 3]})

    def bad_to_csv(*a, **k):
        out_file.write_text("garbage")  # simulate half-written file
        raise Exception("forced fail")

    df.to_csv = bad_to_csv

    leaderboard.export_leaderboard(df, out_file)

    # Ensure cleanup happened
    assert not out_file.exists()
    assert "failed" in caplog.text.lower()
