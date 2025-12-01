from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

EV_JSON = Path("config") / "phase5" / "ev_simple.json"
BANDS_YAML = Path("config") / "phase5_ev_bands.yml"

NVDA_CSV = Path("logs") / "nvda_phase5_paper_for_notion.csv"
SPY_CSV  = Path("logs") / "spy_phase5_paper_for_notion.csv"
QQQ_CSV  = Path("logs") / "qqq_phase5_paper_for_notion.csv"


def _load_ev_simple() -> Dict[str, float]:
    """
    Load per-trade EVs from ev_simple.json into a flat dict of regime -> EV.
    """
    out: Dict[str, float] = {}
    if not EV_JSON.exists():
        return out

    with EV_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # NVDA stored as scalar
    nvda_val = data.get("NVDA_BPLUS_LIVE")
    if nvda_val is not None:
        try:
            out["NVDA_BPLUS_LIVE"] = float(nvda_val)
        except (TypeError, ValueError):
            pass

    # SPY / QQQ stored as dicts with ev_per_trade
    for key in ("SPY_ORB_LIVE", "QQQ_ORB_LIVE"):
        cfg = data.get(key)
        if isinstance(cfg, dict):
            v = cfg.get("ev_per_trade")
            if v is not None:
                try:
                    out[key] = float(v)
                except (TypeError, ValueError):
                    pass

    return out


def _load_bands_yaml() -> Dict[str, float]:
    """
    Very small YAML reader specialized for phase5_ev_bands.yml format:
        regime_lowercase:
          ev_band_abs: 0.0123
    """
    if not BANDS_YAML.exists():
        return {}

    text = BANDS_YAML.read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in text.splitlines()]

    bands: Dict[str, float] = {}
    current_key: Optional[str] = None

    for ln in lines:
        line = ln.strip()
        if not line or line.startswith("#"):
            continue

        # regime key line: nvda_bplus_live:
        if line.endswith(":") and not line.startswith("ev_band_abs"):
            current_key = line.rstrip(":").strip()
            continue

        if line.startswith("ev_band_abs:") and current_key:
            _, val_str = line.split(":", 1)
            val_str = val_str.strip()
            try:
                bands[current_key] = float(val_str)
            except ValueError:
                pass

    return bands


def _load_csv(path: Path, regime: str) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("regime") == regime and row.get("side") == "SELL":
                rows.append(row)
    return rows


def _classify_by_band(rows: List[Dict[str, str]], band_abs: float) -> Tuple[int, int]:
    """
    Return (inside, outside) counts where:
      inside  = |ev| >= band_abs
      outside = |ev| <  band_abs
    """
    inside = 0
    outside = 0

    for r in rows:
        ev_str = r.get("ev")
        if ev_str is None:
            continue
        try:
            ev = float(ev_str)
        except (TypeError, ValueError):
            continue

        if abs(ev) >= band_abs:
            inside += 1
        else:
            outside += 1

    return inside, outside


def main() -> None:
    ev_cfg = _load_ev_simple()
    bands = _load_bands_yaml()

    print("[EV] ev_simple.json snapshot:")
    for key in ("NVDA_BPLUS_LIVE", "SPY_ORB_LIVE", "QQQ_ORB_LIVE"):
        print(f"  {key:15s} -> {ev_cfg.get(key)!r}")
    print()

    print("[BANDS] phase5_ev_bands.yml snapshot:")
    for key in ("nvda_bplus_live", "spy_orb_live", "qqq_orb_live"):
        print(f"  {key:15s} -> ev_band_abs={bands.get(key)!r}")
    print()

    regimes = [
        ("NVDA_BPLUS_LIVE", "nvda_bplus_live", NVDA_CSV),
        ("SPY_ORB_LIVE",    "spy_orb_live",    SPY_CSV),
        ("QQQ_ORB_LIVE",    "qqq_orb_live",    QQQ_CSV),
    ]

    print("[BANDS] EV vs ev_band_abs classification (SELL, RequireEv-style)...")
    print()
    print(f"{'Regime':15s} {'BandAbs':>10s} {'Trades':>8s} {'|ev|>=band':>12s} {'|ev|<band':>10s}")

    for regime, band_key, csv_path in regimes:
        band_abs = bands.get(band_key)
        if band_abs is None:
            print(f"{regime:15s} {'-':>10s} {'-':>8s} {'-':>12s} {'-':>10s}")
            continue

        rows = _load_csv(csv_path, regime)
        inside, outside = _classify_by_band(rows, band_abs)
        total = inside + outside

        print(
            f"{regime:15s} "
            f"{band_abs:10.4f} "
            f"{total:8d} "
            f"{inside:12d} "
            f"{outside:10d}"
        )


if __name__ == "__main__":
    main()