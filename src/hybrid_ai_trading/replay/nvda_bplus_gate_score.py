from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import csv
from typing import Optional


@dataclass
class GateScoreHealth:
    symbol: str
    count_signals: int
    pnl_samples: int
    mean_edge_ratio: float
    mean_micro_score: float
    mean_pnl: float


def _parse_int(row: dict, key: str, default: int = 0) -> int:
    try:
        val = row.get(key)
        if val is None or val == "":
            return default
        return int(val)
    except (TypeError, ValueError):
        return default


def _parse_float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        val = row.get(key)
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def load_nvda_gatescore_health(repo_root: Optional[Path] = None) -> GateScoreHealth:
    """
    Load the latest GateScore summary for NVDA from logs/gatescore_pnl_summary.csv.

    This is used by tools/_nvda_gate_score_smoke.py and Phase-3 diagnostics.
    """
    if repo_root is None:
        # .../src/hybrid_ai_trading/replay/nvda_bplus_gate_score.py -> repo root = parents[3]
        repo_root = Path(__file__).resolve().parents[3]

    csv_path = repo_root / "logs" / "gatescore_pnl_summary.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"GateScore PnL summary not found at {csv_path}")

    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        nvda_rows = [row for row in reader if row.get("symbol") == "NVDA"]

    if not nvda_rows:
        raise ValueError("No NVDA rows found in gatescore_pnl_summary.csv")

    # Use the last row for NVDA as the current summary
    row = nvda_rows[-1]

    return GateScoreHealth(
        symbol="NVDA",
        count_signals=_parse_int(row, "count_signals", 0),
        pnl_samples=_parse_int(row, "pnl_samples", 0),
        mean_edge_ratio=_parse_float(row, "mean_edge_ratio", 0.0),
        mean_micro_score=_parse_float(row, "mean_micro_score", 0.0),
        mean_pnl=_parse_float(row, "mean_pnl", 0.0),
    )

def compute_nvda_gatescore_today(repo_root: Optional[Path] = None) -> float:
    """
    TRUE ORB+VWAP GateScore (deterministic, replay-driven, NO GUESSING).

    Strict ORB: orb_n = min(15, len(bars)-1)  (always leaves >=1 post bar)
    VWAP confirm:
      - Long trigger: high >= ORH and close >= vwap
      - Short trigger: low  <= ORL and close <= vwap

    Score mapping (locked to decision rules):
      +1.0 = first confirmed LONG breakout
      -1.0 = first confirmed SHORT breakout
       0.0 = no confirmed breakout

    Exports honest diagnostics:
      _NVDA_GS_COUNT_SIGNALS = number of post bars that hit either trigger
      _NVDA_GS_PNL_SAMPLES   = number of post bars
    """
    import os
    import csv
    from pathlib import Path

    rr = repo_root or Path(__file__).resolve().parents[3]
    fixture = (os.environ.get("HAT_NVDA_REPLAY_CSV") or "").strip()
    if fixture:
        csv_path = Path(fixture)
    else:
        csv_path = rr / "data" / "nvda_1min_sample.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Replay NVDA CSV not found at {csv_path}")

    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                ts = row.get("timestamp")
                if not ts:
                    continue
                o = float(row["open"])
                h = float(row["high"])
                l = float(row["low"])
                c = float(row["close"])
                v = float(row.get("volume") or 0.0)
            except Exception:
                continue
            rows.append((ts, o, h, l, c, v))

    if len(rows) < 3:
        raise ValueError("Not enough replay bars for ORB+VWAP (need >=3)")

    rows.sort(key=lambda x: x[0])

    # VWAP cumulative (typical price * vol)
    vwap_list = []
    num = 0.0
    den = 0.0
    for (_, o, h, l, c, v) in rows:
        w = v if v > 0 else 1.0
        tp = (h + l + c) / 3.0
        num += tp * w
        den += w
        vwap_list.append(num / max(1e-9, den))

    orb_n = min(15, len(rows) - 1)
    orb = rows[:orb_n]
    orh = max(x[2] for x in orb)
    orl = min(x[3] for x in orb)

    post_rows = rows[orb_n:]
    post_vwaps = vwap_list[orb_n:]
    pnl_samples = len(post_rows)

    count_signals = 0
    long_hits = []
    short_hits = []
    for i in range(len(post_rows)):
        (_, o, h, l, c, v) = post_rows[i]
        vw = post_vwaps[i]
        long_ok = (h >= orh) and (c >= vw)
        short_ok = (l <= orl) and (c <= vw)
        if long_ok or short_ok:
            count_signals += 1
        if long_ok:
            long_hits.append(i)
        if short_ok:
            short_hits.append(i)

    globals()["_NVDA_GS_COUNT_SIGNALS"] = int(count_signals)
    globals()["_NVDA_GS_PNL_SAMPLES"] = int(pnl_samples)

    first_long = long_hits[0] if long_hits else None
    first_short = short_hits[0] if short_hits else None

    if first_long is None and first_short is None:
        return 0.0
    if first_short is None:
        return 1.0
    if first_long is None:
        return -1.0
    return 1.0 if first_long <= first_short else -1.0

def main() -> int:
    """
    Phase-1 canonical entrypoint (deterministic, testable).

    Contract:
      - returns 0 on success
      - returns non-zero on failure
    """
    try:
        # If this module already exposes a CLI-style entrypoint, prefer it.
        if "cli" in globals() and callable(globals().get("cli")):
            out = globals()["cli"]()
            return int(out) if out is not None else 0

        # If there is a common runner function, call it with safe defaults.
        for nm in ("compute_nvda_gatescore_today", "load_nvda_gatescore_health", "run", "run_replay", "compute", "compute_gatescore", "gate_score", "gatescore"):
            fn = globals().get(nm)
            if callable(fn):
                out = fn()
                # Phase-1 smoke contract: success means "ran deterministically" (rc=0),
                # regardless of strategy direction (-1/0/+1).
                try:
                    print(f"[PHASE1] gatescore_out={out}")
                    print(f"[PHASE1] _NVDA_GS_COUNT_SIGNALS={globals().get('_NVDA_GS_COUNT_SIGNALS')}")
                    print(f"[PHASE1] _NVDA_GS_PNL_SAMPLES={globals().get('_NVDA_GS_PNL_SAMPLES')}")
                except Exception:
                    pass
                return 0

        # Fallback: if the file was meant to be executed for side effects,
        # then reaching here means "nothing callable" -> fail-closed.
        print("[PHASE1] FAIL-CLOSED: no callable entrypoint (expected cli/run/compute/*) in nvda_bplus_gate_score.py")
        return 2
    except SystemExit as e:
        # argparse patterns often raise SystemExit
        try:
            return int(getattr(e, "code", 1) or 0)
        except Exception:
            return 1
    except Exception as e:
        print(f"[PHASE1] FAIL-CLOSED: exception in main(): {type(e).__name__}: {e}")
        return 1



