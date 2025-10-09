"""
Paper Trade Demo (Hybrid AI Quant Pro – Live Ready)
- Breakout signal on BTC/USD
- Timezone-aware UTC stamping
- Provides run_paper_trade(engine=None) for main.py compatibility
"""

import logging
from datetime import datetime, timezone

from hybrid_ai_trading.signals.breakout_v1 import breakout_signal

logger = logging.getLogger(__name__)


def _now():
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def run_demo():
    """Simple demonstration of breakout_signal with logging."""
    try:
        sig = breakout_signal("BITSTAMP_SPOT_BTC_USD")
        msg = f"[{_now()}] Breakout signal: {sig}"
        print(msg)
        logger.info(msg)
    except Exception as e:
        msg = f"[{_now()}] Breakout signal failed: {e}"
        print(msg)
        logger.error(msg)


def run_paper_trade(_engine=None):
    """Compatibility wrapper expected by main.py."""
    run_demo()


if __name__ == "__main__":
    run_demo()
