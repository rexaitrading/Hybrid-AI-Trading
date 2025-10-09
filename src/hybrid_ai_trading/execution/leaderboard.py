"""
Leaderboard Exporter (Hybrid AI Quant Pro – Hedge-Fund Grade)
-------------------------------------------------------------
Provides a robust export function for leaderboard DataFrames.

Features:
- Always writes headers (even if DataFrame is empty)
- Logs warnings for empty input
- Logs success on valid export
- Handles exceptions gracefully (removes half-written files)
"""

import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


def export_leaderboard(df: pd.DataFrame, out_file: Path) -> None:
    """
    Export a leaderboard DataFrame to CSV.

    Parameters
    ----------
    df : pd.DataFrame
        Leaderboard data to export.
    out_file : Path
        Target CSV file path.

    Behavior
    --------
    - If `df` is empty: writes only headers, logs a warning.
    - If `df` is valid: writes full CSV, logs success.
    - On error: logs the failure and removes any half-written file.
    """
    try:
        if df.empty:
            logger.warning("⚠️ Empty leaderboard → writing headers only")
            # Always write headers even if no rows
            df.to_csv(out_file, index=False)
            return

        df.to_csv(out_file, index=False)
        logger.info("✅ Leaderboard exported to %s", out_file)

    except Exception as e:
        logger.error("❌ Failed to export leaderboard: %s", e, exc_info=True)
        # Ensure no corrupted file remains
        if out_file.exists():
            try:
                out_file.unlink()
                logger.debug("🗑️ Removed half-written file: %s", out_file)
            except Exception as cleanup_error:
                logger.debug("⚠️ Failed to cleanup file: %s", cleanup_error)
