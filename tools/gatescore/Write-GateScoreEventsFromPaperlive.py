# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = (ln or "").strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out

def _asof(x: Any) -> str:
    s = str(x or "").strip()
    return s[:10]

def _bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    s = str(x or "").strip().lower()
    return s in ("1", "true", "yes", "y", "t")

def _float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def _int(x: Any) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0

def _pick_inputs(logs: Path, sym: str) -> Path:
    m = {
        "NVDA": logs / "nvda_phase5_paperlive_results.jsonl",
        "SPY": logs / "spy_phase5_paperlive_results.jsonl",
        "QQQ": logs / "qqq_phase5_paperlive_results.jsonl",
    }
    return m[sym]

def _out_events_path(logs: Path, sym: str) -> Path:
    m = {
        "NVDA": logs / "nvda_gatescore_events.jsonl",
        "SPY": logs / "spy_gatescore_events.jsonl",
        "QQQ": logs / "qqq_gatescore_events.jsonl",
    }
    return m[sym]

def _emit_event(sym: str, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Required fields used by daily_summary_from_events.py:
    # as_of_date, symbol, edge_ratio, micro_score, pnl_samples, count_signals, realized_pnl (optional)
    as_of = _asof(row.get("as_of_date"))
    if not as_of:
        return None

    # tighten-only: ignore synthetic rows (do not help GateScore)
    if _bool(row.get("is_synthetic", False)):
        return None

    # if edge/micro missing, still produce (they'll default to 0 in aggregator)
    edge = _float(row.get("edge_ratio"))
    micro = _float(row.get("micro_score"))

    # pnl evidence: require realized pnl OR explicit pnl_samples > 0
    pnl_samples = _int(row.get("pnl_samples", 0))
    realized = _float(row.get("realized_pnl"))

    # Many of your paper_runner rows contain count_signals; default 1
    count_signals = _int(row.get("count_signals", 1))
    if count_signals <= 0:
        count_signals = 1

    ev: Dict[str, Any] = {
        "as_of_date": as_of,
        "symbol": sym,
        "source": row.get("source", "paperlive"),
        "edge_ratio": edge if edge is not None else 0.0,
        "micro_score": micro if micro is not None else 0.0,
        "pnl_samples": pnl_samples,
        "count_signals": count_signals,
    }
    if realized is not None:
        ev["realized_pnl"] = realized
    return ev

def main() -> int:
    ap = argparse.ArgumentParser("Write GateScore events from paperlive results (fail-closed, no synthetic).")
    ap.add_argument("--as-of-date", default=os.environ.get("HAT_ASOF_DATE", "").strip())
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--symbols", default="NVDA,SPY,QQQ")
    args = ap.parse_args()

    as_of = (args.as_of_date or "").strip()[:10]
    if not as_of:
        print(json.dumps({"ok": False, "reason": "missing_as_of_date"}, indent=2))
        return 2

    logs = Path(args.logs)
    syms = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
    for sym in syms:
        if sym not in ("NVDA", "SPY", "QQQ"):
            print(json.dumps({"ok": False, "reason": "bad_symbol", "symbol": sym}, indent=2))
            return 2

    wrote = {}
    any_rows = False

    for sym in syms:
        inp = _pick_inputs(logs, sym)
        rows = _read_jsonl(inp)

        # Filter to today and emit events
        out_events: List[Dict[str, Any]] = []
        for r in rows:
            if _asof(r.get("as_of_date")) != as_of:
                continue
            ev = _emit_event(sym, r)
            if ev is None:
                continue
            out_events.append(ev)

        # Write (always overwrite for determinism)
        outp = _out_events_path(logs, sym)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text("\n".join(json.dumps(x, separators=(",", ":")) for x in out_events) + ("\n" if out_events else ""), encoding="utf-8")

        wrote[sym] = {"in": str(inp), "out": str(outp), "rows": len(out_events)}
        if out_events:
            any_rows = True

    # Fail-closed if nothing written for ALL requested symbols
    ok = bool(any_rows)
    print(json.dumps({"ok": ok, "as_of_date": as_of, "wrote": wrote}, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
