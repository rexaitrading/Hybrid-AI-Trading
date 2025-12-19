from __future__ import annotations
import json
from pathlib import Path

def main() -> int:
    logs = Path("logs")
    # pick newest file that looks like a phase2 micro snapshot
        # Prefer explicit NVDA micro artifact first
    p0 = logs / "nvda_micro_for_gatescore.json"
    if p0.exists():
        try:
            obj = json.loads(p0.read_text(encoding="utf-8"))
            v = obj.get("micro_score", 0.0)
            print(float(v))
            return 0
        except Exception:
            pass

    cands = sorted(
        [p for p in logs.glob("*") if p.is_file() and ("micro" in p.name.lower() or "phase2" in p.name.lower())],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cands:
        print("0.0")
        return 0

    p = cands[0]
    # Minimal: if json has a micro_score field, use it; else fail-closed to 0.0
    try:
        if p.suffix.lower() == ".json":
            obj = json.loads(p.read_text(encoding="utf-8"))
            v = obj.get("micro_score", 0.0)
            print(float(v))
            return 0
    except Exception:
        pass

    # Unknown schema -> fail-closed
    print("0.0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

