"""
Black Swan Guard

This module acts as a safety filter on top of trading signals.
It blocks trades if potential black swan / anomaly conditions are detected.

Configured in config/config.yaml under:
features:
  enable_black_swan_guard: true
  black_swan_sources:
    - "news_sentiment_ai"
    - "orderbook_anomaly_ai"
    - "macro_alert_ai"
"""

from src.config.settings import load_config


class BlackSwanGuard:
    def __init__(self):
        self.cfg = load_config()
        self.enabled = self.cfg["features"].get("enable_black_swan_guard", False)
        self.sources = self.cfg["features"].get("black_swan_sources", [])
        self.flags = {src: False for src in self.sources}  # track active anomaly flags

    def trigger_event(self, source: str, reason: str = ""):
        """Manually trigger a black swan event from a given source."""
        if source in self.flags:
            self.flags[source] = True
            print(f"[BLACK SWAN] {source} triggered: {reason}")

    def clear_event(self, source: str):
        """Clear an anomaly flag for a given source."""
        if source in self.flags:
            self.flags[source] = False
            print(f"[BLACK SWAN] {source} cleared.")

    def active(self) -> bool:
        """Return True if any black swan guard is currently active."""
        if not self.enabled:
            return False
        return any(self.flags.values())

    def filter_signal(self, signal: str) -> str:
        """Return HOLD if black swan active, otherwise pass the signal."""
        if self.active():
            print("[BLACK SWAN] Blocking trade due to active anomaly flag.")
            return "HOLD"
        return signal
