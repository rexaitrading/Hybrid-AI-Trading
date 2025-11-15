from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any


class Provider(str, Enum):
    IBKR = "ibkr"
    TMX = "tmx"
    KRAKEN = "kraken"
    COINBASE = "coinbase"
    OANDA = "oanda"


@dataclass
class QosEvent:
    provider: Provider
    ts_ns: int
    op: str  # e.g. "tick", "snapshot", "order", "health"
    latency_ms: Optional[float] = None
    freshness_ms: Optional[float] = None
    ok: bool = True
    error: Optional[str] = None
    symbol: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    @classmethod
    def now(
        cls,
        provider: Provider,
        op: str,
        latency_ms: Optional[float] = None,
        freshness_ms: Optional[float] = None,
        ok: bool = True,
        error: Optional[str] = None,
        symbol: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "QosEvent":
        return cls(
            provider=provider,
            ts_ns=time.time_ns(),
            op=op,
            latency_ms=latency_ms,
            freshness_ms=freshness_ms,
            ok=ok,
            error=error,
            symbol=symbol,
            extra=extra or {},
        )


class ProviderQosLedger:
    """
    Append-only JSONL ledger per provider.

    Files:
        .intel/providers/ibkr.qos.jsonl
        .intel/providers/tmx.qos.jsonl
        ...
    """

    def __init__(self, root: str) -> None:
        # repo root; we will write under .intel/providers
        self._root = root
        self._dir = os.path.join(root, ".intel", "providers")
        os.makedirs(self._dir, exist_ok=True)

    def _path_for(self, provider: Provider) -> str:
        return os.path.join(self._dir, f"{provider.value}.qos.jsonl")

    def append(self, event: QosEvent) -> None:
        path = self._path_for(event.provider)
        line = json.dumps(asdict(event), separators=(",", ":"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def mark_ok(
        self,
        provider: Provider,
        op: str,
        latency_ms: Optional[float],
        freshness_ms: Optional[float],
        symbol: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.append(
            QosEvent.now(
                provider=provider,
                op=op,
                latency_ms=latency_ms,
                freshness_ms=freshness_ms,
                ok=True,
                error=None,
                symbol=symbol,
                extra=extra,
            )
        )

    def mark_error(
        self,
        provider: Provider,
        op: str,
        error: str,
        symbol: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.append(
            QosEvent.now(
                provider=provider,
                op=op,
                latency_ms=None,
                freshness_ms=None,
                ok=False,
                error=error,
                symbol=symbol,
                extra=extra,
            )
        )