from __future__ import annotations

import json
from pathlib import Path

def test_phase4_validation_stamp_schema_ci_safe():
    p = Path("logs/phase4_validation_passed.json")
    if not p.exists():
        # CI-safe: absence allowed, but schema enforced when present
        return

    obj = json.loads(p.read_text(encoding="utf-8-sig"))
    assert "as_of_date" in obj
    assert "phase4_ok_today" in obj
    assert isinstance(obj["as_of_date"], str)
    assert isinstance(obj["phase4_ok_today"], bool)
