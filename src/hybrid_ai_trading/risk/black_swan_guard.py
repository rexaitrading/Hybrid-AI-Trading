"""
Black Swan Guard (Hybrid AI Quant Pro v12.6 – Polished & 100% Coverage)
-----------------------------------------------------------------------
- Blocks trades when catastrophic events are triggered
- Supports multiple active events
- Provides clear_event() and clear_all() to reset guard
- Structured logging consistent with other Risk modules
"""

import logging
from typing import Dict

logger = logging.getLogger("hybrid_ai_trading.risk.black_swan_guard")


class BlackSwanGuard:
    def __init__(self) -> None:
        # Map: event source → reason
        self.events: Dict[str, str] = {}

    # --------------------------------------------------
    def trigger_event(self, source: str, reason: str = "unspecified") -> None:
        """Activate guard due to a catastrophic event."""
        self.events[source] = reason
        logger.warning(
            f"[BlackSwanGuard] ⚠️ Triggered | source={source}, reason={reason}"
        )

    def clear_event(self, source: str) -> None:
        """Clear a specific event if it exists."""
        if source in self.events:
            logger.info(f"[BlackSwanGuard] ✅ Event Cleared | source={source}")
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
        Block trades if a black swan is active.
        - If active, BUY/SELL → HOLD
        - HOLD always passes
        - Unknown signals unchanged
        """
        if not self.active():
            return signal

        if signal.upper() in {"BUY", "SELL"}:
            logger.warning(
                f"[BlackSwanGuard] ❌ Trade Blocked | signal={signal}, "
                f"active_events={list(self.events.keys())}"
            )
            return "HOLD"

        return signal


__all__ = ["BlackSwanGuard"]
