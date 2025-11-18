from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderHealth:
    name: str
    ok: bool
    latency_s: float
    status_code: Optional[int] = None
    freshness_s: Optional[float] = None


def choose_crypto_provider(
    kraken: ProviderHealth,
    coinbase: ProviderHealth,
) -> str:
    """
    Minimal router for crypto:

      - Prefer kraken when it is healthy and not too slow.
      - Otherwise, fall back to coinbase if healthy.
      - If both are unhealthy, return "none".

    This is a pure policy function; collecting ProviderHealth
    from QoS JSONL is a separate concern.
    """
    # Primary: kraken
    if kraken.ok and (kraken.latency_s <= 0.5):
        return "kraken_primary"

    # Backup: coinbase
    if coinbase.ok:
        return "coinbase_backup"

    return "none"