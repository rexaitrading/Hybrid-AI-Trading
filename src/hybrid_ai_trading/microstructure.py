from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class MicrostructureFeatures:
    """
    Compact summary of short-horizon microstructure state for a symbol.
    All fields are optional-friendly and safe to log as JSON.
    """

    last_ret: float
    window_ret: float
    volume_sum: float

    imbalance: Optional[float] = None          # [-1, 1] if buy/sell volumes provided
    signed_volume: Optional[float] = None      # volume aligned with up/down moves

    spread_now: Optional[float] = None
    spread_avg: Optional[float] = None

    # Final scalar summary in [-1, 1]; positive = buy pressure, negative = sell pressure
    score: float = 0.0


def _safe_pct(a: float, b: float) -> float:
    if b == 0.0:
        return 0.0
    return (a / b) - 1.0


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def compute_microstructure_features(
    closes: Sequence[float],
    volumes: Sequence[float],
    buy_volumes: Optional[Sequence[float]] = None,
    sell_volumes: Optional[Sequence[float]] = None,
    spreads: Optional[Sequence[float]] = None,
) -> MicrostructureFeatures:
    """
    Compute basic microstructure features from recent bars.

    Assumptions:
        - closes and volumes are aligned and length >= 2.
        - buy_volumes / sell_volumes are optional; if omitted, imbalance is None.
        - spreads is optional; if omitted, spread fields are None.

    This intentionally avoids external dependencies (no numpy/pandas).
    """
    if len(closes) < 2 or len(volumes) < 2:
        # Degenerate case; return zeros
        return MicrostructureFeatures(
            last_ret=0.0,
            window_ret=0.0,
            volume_sum=0.0,
            imbalance=None,
            signed_volume=None,
            spread_now=None,
            spread_avg=None,
            score=0.0,
        )

    n = len(closes)
    last_ret = _safe_pct(closes[-1], closes[-2])
    window_ret = _safe_pct(closes[-1], closes[0])
    volume_sum = float(sum(volumes))

    # Signed volume proxy: volume with sign of price change per bar
    signed_volume = 0.0
    for i in range(1, n):
        bar_ret = closes[i] - closes[i - 1]
        v = volumes[i]
        if bar_ret > 0:
            signed_volume += v
        elif bar_ret < 0:
            signed_volume -= v
        # bar_ret == 0 -> no contribution

    # Imbalance based on aggressive buy/sell if provided
    imbalance: Optional[float]
    if buy_volumes is not None and sell_volumes is not None:
        if len(buy_volumes) == n and len(sell_volumes) == n:
            buy_sum = float(sum(buy_volumes))
            sell_sum = float(sum(sell_volumes))
            denom = buy_sum + sell_sum
            if denom > 0.0:
                imbalance = _clamp((buy_sum - sell_sum) / denom, -1.0, 1.0)
            else:
                imbalance = None
        else:
            imbalance = None
    else:
        imbalance = None

    # Spread statistics if provided
    spread_now: Optional[float]
    spread_avg: Optional[float]
    if spreads is not None and len(spreads) > 0:
        spread_now = float(spreads[-1])
        spread_avg = float(sum(spreads) / len(spreads))
    else:
        spread_now = None
        spread_avg = None

    # Basic scoring heuristic:
    # - Strong positive returns + signed_volume > 0 -> +score
    # - Strong negative returns + signed_volume < 0 -> -score
    # - Imbalance adjusts score when available
    score = 0.0

    # Return & signed volume contribution
    rv = last_ret
    sv = signed_volume

    if rv > 0 and sv > 0:
        score += min(abs(rv) * 10.0, 0.4)  # cap contribution
    elif rv < 0 and sv < 0:
        score -= min(abs(rv) * 10.0, 0.4)

    # Window return context
    if window_ret > 0:
        score += min(abs(window_ret) * 5.0, 0.2)
    elif window_ret < 0:
        score -= min(abs(window_ret) * 5.0, 0.2)

    # Imbalance contribution
    if imbalance is not None:
        score += 0.3 * imbalance

    # Spread penalty: wide spreads reduce confidence
    if spread_now is not None and spread_avg is not None and spread_avg > 0.0:
        wideness = spread_now / spread_avg
        if wideness > 1.5:
            score *= 0.7
        elif wideness > 2.0:
            score *= 0.5

    score = _clamp(score, -1.0, 1.0)

    return MicrostructureFeatures(
        last_ret=last_ret,
        window_ret=window_ret,
        volume_sum=volume_sum,
        imbalance=imbalance,
        signed_volume=signed_volume,
        spread_now=spread_now,
        spread_avg=spread_avg,
        score=score,
    )


class MicrostructureTelemetryWriter:
    """
    JSONL writer for microstructure snapshots.

    Default location:
        <repo_root>/.intel/microstructure.jsonl

    Best-effort only: all errors are swallowed after logging.
    """

    def __init__(self, root: Optional[str] = None) -> None:
        if root is None:
            # microstructure.py -> src/hybrid_ai_trading -> src -> repo root
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self._root = root
        intel_dir = os.path.join(self._root, ".intel")
        os.makedirs(intel_dir, exist_ok=True)
        self._path = os.path.join(intel_dir, "microstructure.jsonl")

    def write(self, symbol: str, features: MicrostructureFeatures) -> None:
        try:
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            payload: Dict[str, Any] = {
                "ts_utc": ts,
                "symbol": symbol,
                "features": asdict(features),
            }
            line = json.dumps(payload, ensure_ascii=False)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # Swallow all errors; this must never break the trading loop.
            return


def _is_enabled() -> bool:
    """
    Env gate for microstructure telemetry.

    HAT_MICRO_ENABLE in {"1", "true", "TRUE", "yes", "YES"} enables logging.
    """
    val = os.environ.get("HAT_MICRO_ENABLE")
    if not val:
        return False
    return val in {"1", "true", "TRUE", "yes", "YES"}


def record_microstructure(
    symbol: str,
    closes: Sequence[float],
    volumes: Sequence[float],
    buy_volumes: Optional[Sequence[float]] = None,
    sell_volumes: Optional[Sequence[float]] = None,
    spreads: Optional[Sequence[float]] = None,
) -> MicrostructureFeatures:
    """
    Convenience helper:

        feats = record_microstructure(
            symbol="AAPL",
            closes=closes_window,
            volumes=volumes_window,
            buy_volumes=buy_vols_window,   # optional
            sell_volumes=sell_vols_window, # optional
            spreads=spreads_window,        # optional
        )

    Returns MicrostructureFeatures and, if enabled, logs to .intel/microstructure.jsonl.
    """
    feats = compute_microstructure_features(
        closes=closes,
        volumes=volumes,
        buy_volumes=buy_volumes,
        sell_volumes=sell_volumes,
        spreads=spreads,
    )

    if _is_enabled():
        writer = MicrostructureTelemetryWriter()
        writer.write(symbol, feats)

    return feats
    """
    Classify microstructure regime as 'GREEN', 'CAUTION', or 'RED'.
    """
    try:
        r = float(ms_range_pct)
    except (TypeError, ValueError):
        r = 0.0

    try:
        spread = float(est_spread_bps)
    except (TypeError, ValueError):
        spread = 0.0

    try:
        fee = float(est_fee_bps)
    except (TypeError, ValueError):
        fee = 0.0

    total_cost = spread + fee

    if total_cost <= 1.0 and r <= 0.003:
        return "GREEN"
    if total_cost <= 2.0 and r <= 0.007:
        return "CAUTION"
    return "RED"
def classify_micro_regime(ms_range_pct: float, est_spread_bps: float, est_fee_bps: float) -> str:
    """
    Classify microstructure regime as 'GREEN', 'CAUTION', or 'RED'.
    """
    try:
        r = float(ms_range_pct)
    except (TypeError, ValueError):
        r = 0.0

    try:
        spread = float(est_spread_bps)
    except (TypeError, ValueError):
        spread = 0.0

    try:
        fee = float(est_fee_bps)
    except (TypeError, ValueError):
        fee = 0.0

    total_cost = spread + fee

    if total_cost <= 1.0 and r <= 0.003:
        return "GREEN"
    if total_cost <= 2.0 and r <= 0.007:
        return "CAUTION"
    return "RED"

