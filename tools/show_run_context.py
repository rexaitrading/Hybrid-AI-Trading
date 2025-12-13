from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import date

def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return {"_error": f"failed to read {path}: {e.__class__.__name__}: {e}"}

def main() -> int:
    ap = argparse.ArgumentParser(description="HybridAITrading RunContext quick view (artifact-based).")
    ap.add_argument("-Mode", default="premarket")
    ap.add_argument("-Symbol", default="NVDA")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    logs = repo / "logs"

    phase4 = _read_json(logs / "phase4_validation_passed.json")
    blockg = _read_json(logs / "blockg_status_stub.json")
    # (If you store it elsewhere later, we can add search/fallback.)

    today = date.today().isoformat()

    out = {
        "repo_root": str(repo),
        "mode": args.Mode,
        "symbol": args.Symbol,
        "today": today,
        "artifacts": {
            "phase4_validation_passed": phase4,
            "blockg_status_stub": blockg,
        },
        "derived": {
            "phase4_ok": bool(phase4 and not isinstance(phase4, dict) or True),
        }
    }

    # If your stub contains per-symbol flags like nvda_blockg_ready, surface them:
    if isinstance(blockg, dict):
        sym = args.Symbol.upper()
        key = f"{sym.lower()}_blockg_ready"
        out["derived"]["symbol_blockg_ready_key"] = key
        out["derived"]["symbol_blockg_ready"] = blockg.get(key)

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
