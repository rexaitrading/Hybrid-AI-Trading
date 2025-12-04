from datetime import datetime
import sys
from pathlib import Path

# --- Ensure src/ is on sys.path so hybrid_ai_trading is importable ---
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hybrid_ai_trading.utils.paper_exec_logger import log_paper_exec


def main() -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    log_paper_exec({
        "ts_trade": ts,
        "symbol": "NVDA",
        "side": "long",
        "qty": 10,
        "entry_px": 100.25,
        "pnl_pct": 0.0,
        "regime": "TEST_PAPER_HOOK",
        "session": "TEST_SMOKE",
    })
    print("Wrote test paper exec at", ts)


if __name__ == "__main__":
    main()
def test_paper_exec_logger_smoke() -> None:
    """
    Pytest wrapper that exercises main() once. This ensures that the
    paper_exec_logger smoke script can run end-to-end and write a
    single test paper exec entry without raising exceptions.
    """
    main()