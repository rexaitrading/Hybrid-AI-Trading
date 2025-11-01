from __future__ import annotations

import datetime
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple

REPLAY_PATH = os.environ.get("HAT_REPLAY_LOG", r"data/replay_log.ndjson")
OUT_DIR = os.environ.get("HAT_PATTERNS_DIR", r"data/patterns")


def _load_ndjson(path: str) -> Iterable[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _time_bucket(ts_iso: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(ts_iso.replace("Z", ""))
        bucket_min = (dt.minute // 5) * 5
        return f"{dt.hour:02d}:{bucket_min:02d}"
    except Exception:
        return "00:00"


def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _impulse_and_pullback(bars: List[Dict[str, Any]]) -> Tuple[float, float]:
    if not bars:
        return 0.0, 0.0
    highs = [_safe_float(b.get("high")) for b in bars]
    lows = [_safe_float(b.get("low")) for b in bars]
    closes = [_safe_float(b.get("close")) for b in bars]
    imp = (max(highs) - min(lows)) if highs and lows else 0.0
    pb = (max(highs) - closes[-1]) if closes else 0.0
    return imp, pb


def _opening_range(bars: List[Dict[str, Any]], n: int = 5) -> Tuple[float, float]:
    if not bars:
        return 0.0, 0.0
    win = bars[: max(1, min(n, len(bars)))]
    hi = max(_safe_float(b.get("high")) for b in win)
    lo = min(_safe_float(b.get("low")) for b in win)
    return hi, lo


def _evaluate_orb(bars: List[Dict[str, Any]]) -> float:
    if len(bars) < 6:
        return 0.0
    hi, lo = _opening_range(bars, 5)
    last = _safe_float(bars[5].get("close"))
    rng = max(1e-6, hi - lo)
    if last > hi:
        return min(1.0, (last - hi) / rng)
    return 0.0


def _evaluate_vwap_reclaim(bars: List[Dict[str, Any]]) -> float:
    closes = [_safe_float(b.get("close")) for b in bars[-20:]]
    if len(closes) < 5:
        return 0.0
    sma = sum(closes) / len(closes)
    last = closes[-1]
    prev = closes[-2]
    if prev < sma <= last:
        d = max(0.0, last - sma)
        mad = (sum(abs(c - sma) for c in closes) / len(closes)) or 1e-6
        return min(1.0, d / mad)
    return 0.0


def _avg_R(samples: List[float]) -> float:
    if not samples:
        return 0.0
    return sum(samples) / len(samples)


def mine_patterns(replay_stream: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_symbol: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ev in replay_stream:
        sym = ev.get("symbol") or "UNK"
        by_symbol[sym].append(ev)
    patterns = {
        "ORB breakout": {
            "setup": "ORB",
            "context_tags": ["ORB", "Breakout", "Scalp"],
            "samples": [],
            "symbols": Counter(),
        },
        "VWAP reclaim": {
            "setup": "VWAP Reclaim",
            "context_tags": ["VWAP", "Reversal", "Scalp"],
            "samples": [],
            "symbols": Counter(),
        },
    }
    for sym, events in by_symbol.items():
        for ev in events:
            bars = ev.get("window") or ([ev.get("bar")] if ev.get("bar") else [])
            if not bars:
                continue
            oc = _evaluate_orb(bars)
            vc = _evaluate_vwap_reclaim(bars)
            if oc > 0:
                patterns["ORB breakout"]["samples"].append(
                    {
                        "symbol": sym,
                        "r": _safe_float((ev.get("hypo") or {}).get("r"), 0.0),
                        "conf": oc,
                    }
                )
                patterns["ORB breakout"]["symbols"][sym] += 1
            if vc > 0:
                patterns["VWAP reclaim"]["samples"].append(
                    {
                        "symbol": sym,
                        "r": _safe_float((ev.get("hypo") or {}).get("r"), 0.0),
                        "conf": vc,
                    }
                )
                patterns["VWAP reclaim"]["symbols"][sym] += 1
    out: List[Dict[str, Any]] = []
    ts = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    for name, obj in patterns.items():
        smp = obj["samples"]
        if not smp:
            continue
        avg_conf = _avg_R([s["conf"] for s in smp])
        avg_R = _avg_R([s["r"] for s in smp])
        symbols_sorted = [k for k, _ in obj["symbols"].most_common(8)]
        notes = (
            f"{name}: avg_conf={avg_conf:.2f}, avg_R={avg_R:.2f}, samples={len(smp)}"
        )
        out.append(
            {
                "name": name,
                "setup": obj["setup"],
                "context_tags": obj["context_tags"],
                "confidence": round(max(0.0, min(1.0, avg_conf)), 3),
                "regime_conf": 0.5,
                "notes": notes,
                "symbols": symbols_sorted,
                "sample_count": len(smp),
                "avg_R": round(avg_R, 3),
                "ts": ts,
            }
        )
    return out


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    data = list(_load_ndjson(REPLAY_PATH))
    pats = mine_patterns(data)
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    out_path = os.path.join(OUT_DIR, f"candidates_{day}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pats, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
