import json
from pathlib import Path

def _load(sym: str):
    p = Path("logs") / f"{sym.lower()}_gatescore_events.jsonl"
    rows=[]
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def test_spy_qqq_quality_non_toxic_if_eligible_exists():
    # If eligible events exist, enforce minimal quality.
    for sym in ["SPY","QQQ"]:
        rows=_load(sym)
        elig=[r for r in rows if bool(r.get("eligible", False))]
        if not elig:
            # allowed: symbol can be blocked; just don't silently mark eligible
            continue
        # quality constraints
        for r in elig:
            er=float(r.get("edge_ratio",0.0) or 0.0)
            ms=float(r.get("micro_score",0.0) or 0.0)
            assert er >= 0.0
            assert ms > 0.0
