from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from hybrid_ai_trading.risk_config_phase5 import RiskConfigPhase5


def load_phase5_risk_config(config_path: Path) -> tuple[RiskConfigPhase5, list[str] | None]:
    """Load phase5_risk_sketch from the AAPL ORB/VWAP thresholds JSON
    and convert it into a RiskConfigPhase5 instance.

    Notes stored in the JSON sketch are returned separately so we do not
    depend on RiskConfigPhase5 having a `notes` field.
    """
    if not config_path.exists():
        raise SystemExit(f"[AAPL-PHASE5-RISK-SKETCH] Config not found: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))

    sketch = raw.get("phase5_risk_sketch")
    if sketch is None:
        raise SystemExit("[AAPL-PHASE5-RISK-SKETCH] phase5_risk_sketch not present in JSON.")

    # Work on a shallow copy so we can strip out non-dataclass fields.
    sketch_dict = dict(sketch)
    notes = sketch_dict.pop("notes", None)

    cfg = RiskConfigPhase5(**sketch_dict)
    return cfg, notes


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "config" / "orb_vwap_aapl_thresholds.json"

    print("[AAPL-PHASE5-RISK-SKETCH] Repo root:", root)
    print("[AAPL-PHASE5-RISK-SKETCH] Thresholds config:", config_path)

    cfg, notes = load_phase5_risk_config(config_path)

    print("\n[AAPL-PHASE5-RISK-SKETCH] Derived RiskConfigPhase5:")
    for key, value in asdict(cfg).items():
        print(f"  {key:30s} = {value!r}")

    if notes:
        print("\n[AAPL-PHASE5-RISK-SKETCH] Sketch notes from JSON:")
        for line in notes:
            print(f"  - {line}")


if __name__ == "__main__":
    main()