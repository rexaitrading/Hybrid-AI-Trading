from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeterministicLatencyModel:
    """
    Deterministic latency model for backtest/replay.
    """
    order_latency_ms: int = 50
    fill_latency_ms: int = 80

    def total_ms(self) -> int:
        return int(self.order_latency_ms) + int(self.fill_latency_ms)