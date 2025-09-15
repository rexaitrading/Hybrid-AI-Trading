"""
Paper Trade Demo (Hybrid AI Quant Pro v16.8 – 100% Coverage, Final)
-------------------------------------------------------------------
- Calls breakout_signal on BTC/USD.
- Always prints result with UTC timestamp.
- Handles both normal signals and exceptions gracefully.
- Uses _now() wrapper (returns datetime) so tests can patch deterministically.
"""

import logging
from datetime import datetime
from hybrid_ai_trading.signals.breakout_v1 import breakout_signal

logger = logging.getLogger(__name__)


def _now() -> datetime:
    """Return current UTC datetime (can be patched in tests)."""
    return datetime.utcnow()


def run_demo():
    """Run a simple paper trade demo with breakout_signal.

    Prints either:
      - Breakout signal result (BUY/SELL/HOLD)
      - Or an error message if breakout_signal fails
    """
    try:
        sig = breakout_signal("BITSTAMP_SPOT_BTC_USD")
        msg = f"[{_now()}] Breakout signal: {sig}"
        print(msg)
        logger.info(msg)
    except Exception as e:
        msg = f"[{_now()}] Breakout signal failed: {e}"
        print(msg)
        logger.error(msg)


if __name__ == "__main__":
    run_demo()
