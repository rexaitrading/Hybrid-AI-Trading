from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REQUIRED_KEYS = ["as_of_date", "symbol", "edge_ratio", "micro_score", "realized_pnl", "pnl_samples"]

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = (ln or "").strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if isinstance(obj, dict):
            yield obj

def _asof10(s: str) -> str:
    s = (s or "").strip()
    return s[:10] if len(s) >= 10 else s

def _try_float(v: Any) -> Tuple[Optional[float], bool]:
    if v is None:
        return None, False
    try:
        f = float(v)
        # Guard NaN/inf
        if f != f or f in (float("inf"), float("-inf")):
            return None, False
        return f, True
    except Exception:
        return None, False

def _pick_first(obj: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in obj:
            return obj.get(k)
    return None

def _find_replay_output_candidates(logs: Path, as_of: str, symbol: str) -> List[Path]:
    """
    We don't assume a single Phase-1 output name. We search common places.
    Priority: logs/phase1, logs/replay, logs/phase1_artifacts.
    """
    sym = symbol.upper()
    cands: List[Path] = []
    for d in [logs / "phase1", logs / "replay", logs / "phase1_artifacts", logs]:
        if not d.exists():
            continue
        for p in d.glob("*.jsonl"):
            name = p.name.lower()
            if sym.lower() in name and ("replay" in name or "phase1" in name):
                cands.append(p)
    # Also allow generic replay jsonl with per-row symbol field
    for d in [logs / "replay", logs / "phase1"]:
        if not d.exists():
            continue
        for p in d.glob("*.jsonl"):
            if p not in cands:
                cands.append(p)
    return cands

def _convert_row_to_event(row: Dict[str, Any], *, as_of: str, symbol: str) -> Optional[Dict[str, Any]]:
    # Deny synthetic markers
    note = str(row.get("notes", "") or "")
    src = str(row.get("source", "") or "")
    if bool(row.get("is_synthetic", False)) or "synthetic_metrics=true" in note or "paper_runner_stub" in src:
        return None

    # Pick edge/micro from common keys
    edge_v = _pick_first(row, ["edge_ratio", "edge", "mean_edge_ratio", "score", "gatescore_edge"])
    micro_v = _pick_first(row, ["micro_score", "micro", "mean_micro_score", "gatescore_micro"])
    pnl_v = _pick_first(row, ["realized_pnl", "pnl", "pnl_realized", "realizedPnL"])

    edge, ok_edge = _try_float(edge_v)
    micro, ok_micro = _try_float(micro_v)
    rp, ok_rp = _try_float(pnl_v)

    # Require real edge+micro. Fail-closed: do NOT emit if missing/invalid.
    if not ok_edge or not ok_micro:
        return None

    # Evidence-based pnl_samples
    pnl_samples = 1 if ok_rp else 0
    realized_pnl = float(rp) if ok_rp else None

    out = {
        "as_of_date": as_of,
        "symbol": symbol.upper(),
        "source": "replay",
        "edge_ratio": float(edge),
        "micro_score": float(micro),
        "realized_pnl": realized_pnl,
        "pnl_samples": int(pnl_samples),
        "notes": "from_replay",
    }
    # Schema-complete guarantee
    for k in REQUIRED_KEYS:
        if k not in out:
            return None
    return out

def build_events(*, logs: Path, session_path: Path, out_path: Path, min_events: int = 10) -> int:
    if not session_path.exists():
        print(f"[replay->events] missing session: {session_path}")
        return 2
    sess = _load_json(session_path)
    as_of = _asof10(str(sess.get("as_of_date", "") or ""))
    sym = str(sess.get("symbol", "NVDA") or "NVDA").upper().strip() or "NVDA"
    if not as_of:
        print("[replay->events] session missing as_of_date")
        return 2

    cands = _find_replay_output_candidates(logs, as_of, sym)
    if not cands:
        print(f"[replay->events] no replay output candidates found under logs/ for {sym} as_of={as_of}")
        return 4

    emitted: List[str] = []
    for p in cands:
        try:
            for row in _iter_jsonl(p):
                # must match symbol
                r_sym = str(row.get("symbol", "") or row.get("sym", "") or "").upper().strip()
                if r_sym and r_sym != sym:
                    continue
                # must match date if present
                r_as = _asof10(str(row.get("as_of_date", "") or row.get("date", "") or ""))
                if r_as and r_as != as_of:
                    continue
                ev = _convert_row_to_event(row, as_of=as_of, symbol=sym)
                if ev is None:
                    continue
                emitted.append(json.dumps(ev, separators=(",", ":"), ensure_ascii=False))
        except Exception:
            continue

    # Deduplicate exact lines
    emitted = list(dict.fromkeys(emitted))

    if len(emitted) < int(min_events):
        # Fail-closed: do not pollute official events with too-few rows
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8", newline="\n")
        print(f"[replay->events] FAIL-CLOSED: emitted={len(emitted)} < min_events={min_events} (wrote empty official file)")
        return 4

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(emitted) + "\n", encoding="utf-8", newline="\n")
    print(f"[replay->events] wrote {len(emitted)} events -> {out_path}")
    return 0

def main() -> int:
    ap = argparse.ArgumentParser("gatescore.events_from_replay (official, non-synthetic)")
    ap.add_argument("--session", default="logs/replay/replay_session.json")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--out", default="logs/nvda_gatescore_events.jsonl")
    ap.add_argument("--min-events", type=int, default=10)
    args = ap.parse_args()

    root = _repo_root()
    session_path = (root / args.session).resolve()
    logs = (root / args.logs).resolve()
    out_path = (root / args.out).resolve()
    return build_events(logs=logs, session_path=session_path, out_path=out_path, min_events=args.min_events)

if __name__ == "__main__":
    raise SystemExit(main())
