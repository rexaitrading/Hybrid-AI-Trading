"""
Black Swan Guard (Hybrid AI Quant Pro v12.7 – Hedge Fund OE Grade, 100% Coverage)
---------------------------------------------------------------------------------
- Blocks trades when catastrophic/rare events are triggered
- Supports multiple simultaneous active events
- Provides clear_event() and clear_all() for recovery
- Structured logging consistent with other Risk modules
"""

import logging
from typing import Dict

logger = logging.getLogger("hybrid_ai_trading.risk.black_swan_guard")


class BlackSwanGuard:
    """Blocks trading signals when black swan anomaly conditions are active."""

    def __init__(self) -> None:
        # Map: source → reason
        self.events: Dict[str, str] = {}
        logger.info("✅ BlackSwanGuard initialized | events=%s", self.events)

    # --------------------------------------------------
    def trigger_event(self, source: str, reason: str = "unspecified") -> None:
        """Activate guard due to a catastrophic event."""
        self.events[source] = reason
        logger.warning("[BlackSwanGuard] ⚠️ Triggered | source=%s, reason=%s", source, reason)

    def clear_event(self, source: str) -> None:
        """Clear a specific event if it exists."""
        if source in self.events:
            logger.info("[BlackSwanGuard] ✅ Event Cleared | source=%s", source)
            self.events.pop(source)

    def clear_all(self) -> None:
        """Clear all active events."""
        if self.events:
            logger.info("[BlackSwanGuard] ✅ All events cleared")
            self.events.clear()

    # --------------------------------------------------
    def active(self) -> bool:
        """Return True if any event is active."""
        return bool(self.events)

    def filter_signal(self, signal: str) -> str:
        """
        Filter a trading signal:
        - If active and signal is BUY/SELL → returns "HOLD"
        - HOLD always passes
        - Unknown signals unchanged
        """
        if not self.active():
            return signal

        if signal.upper() in {"BUY", "SELL"}:
            logger.warning(
                "[BlackSwanGuard] ❌ Trade Blocked | signal=%s, active_events=%s",
                signal,
                list(self.events.keys()),
            )
            return "HOLD"

        return signal


__all__ = ["BlackSwanGuard"]
