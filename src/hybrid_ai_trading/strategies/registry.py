from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Set, Any


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    symbol: str
    timeframe: str
    supports_modes: Set[str]  # {"REPLAY","PAPER","LIVE"}
    signal_fn: Callable[[dict], dict]
    order_plan_fn: Callable[[dict, object, dict], list]
    logs_schema_version: int = 1


_REGISTRY: Dict[str, StrategySpec] = {}


def register(spec: StrategySpec) -> None:
    sid = (spec.strategy_id or "").strip().upper()
    if not sid:
        raise ValueError("StrategySpec.strategy_id is required")
    if sid in _REGISTRY:
        raise ValueError(f"Duplicate strategy_id: {sid}")
    _REGISTRY[sid] = StrategySpec(
        strategy_id=sid,
        symbol=str(spec.symbol).strip().upper(),
        timeframe=str(spec.timeframe).strip(),
        supports_modes=set(x.strip().upper() for x in spec.supports_modes),
        signal_fn=spec.signal_fn,
        order_plan_fn=spec.order_plan_fn,
        logs_schema_version=int(spec.logs_schema_version),
    )


def get(strategy_id: str) -> Optional[StrategySpec]:
    return _REGISTRY.get((strategy_id or "").strip().upper())


def all_specs() -> Iterable[StrategySpec]:
    return list(_REGISTRY.values())


def clear_registry_for_tests() -> None:
    _REGISTRY.clear()