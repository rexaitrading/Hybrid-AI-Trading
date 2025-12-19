from __future__ import annotations

import os
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_utc(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    # Accept "Z" suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        # treat naive as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _truthy_env(name: str) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _append_arm_event(logs: Path, event: dict) -> None:
    try:
        p = logs / "arm_events.jsonl"
        line = json.dumps(event, ensure_ascii=False)
        with p.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    except Exception:
        # log-only; never break sampling due to audit log
        pass


def _count_today_rows(samples_csv: Path, today: str) -> int:
    if not samples_csv.exists():
        return 0
    try:
        with samples_csv.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            n = 0
            for row in r:
                if not row:
                    continue
                d = (row.get("as_of_date") or "").strip()
                if d == today:
                    n += 1
            return n
    except Exception:
        return 0


def main() -> int:
    # ------------------------------------------------------------
    # PATHS (need repo_root early for audit log)
    # ------------------------------------------------------------
    repo_root = Path(__file__).resolve().parents[1]
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    now_utc = _utc_now()
    today = datetime.now().strftime("%Y-%m-%d")

    # ------------------------------------------------------------
    # HARD SAFETY GATES
    # ------------------------------------------------------------

    # 1) LIVE MODE: absolutely forbidden
    run_mode = (os.environ.get("HAT_RUN_MODE") or "").lower()
    if run_mode == "live":
        _append_arm_event(logs, {
            "ts_utc": now_utc.isoformat(),
            "action": "deny",
            "reason": "live_mode",
        })
        raise SystemExit("Replay GateScore sampling disabled in LIVE mode")

    # 2) ARM INTENT: explicit human intent required
    if not _truthy_env("HAT_ARM_REPLAY_GATESCORE"):
        _append_arm_event(logs, {
            "ts_utc": now_utc.isoformat(),
            "action": "deny",
            "reason": "missing_arm_intent",
        })
        raise SystemExit("Replay GateScore sampling requires HAT_ARM_REPLAY_GATESCORE=1")

    # 3) ARM EXPIRY: must be present + in the future (UTC)
    until_raw = os.environ.get("HAT_ARM_REPLAY_GATESCORE_UNTIL_UTC") or ""
    until_dt = _parse_iso_utc(until_raw)
    if until_dt is None:
        _append_arm_event(logs, {
            "ts_utc": now_utc.isoformat(),
            "action": "deny",
            "reason": "missing_or_bad_expiry",
            "until_utc": until_raw,
        })
        raise SystemExit("Replay GateScore sampling requires HAT_ARM_REPLAY_GATESCORE_UNTIL_UTC=<ISO8601 UTC>")

    if now_utc >= until_dt:
        _append_arm_event(logs, {
            "ts_utc": now_utc.isoformat(),
            "action": "deny",
            "reason": "expiry_elapsed",
            "until_utc": until_dt.isoformat(),
        })
        raise SystemExit("Replay GateScore sampling ARM expired (HAT_ARM_REPLAY_GATESCORE_UNTIL_UTC elapsed)")

    # 4) ARM AUTO-CLEAR AFTER N SAMPLES (per day)
    out = logs / "nvda_gatescore_samples.csv"
    max_samples = int(os.environ.get("HAT_ARM_REPLAY_GATESCORE_MAX_SAMPLES") or "0")
    if max_samples > 0:
        n_today = _count_today_rows(out, today)
        if n_today >= max_samples:
            _append_arm_event(logs, {
                "ts_utc": now_utc.isoformat(),
                "action": "deny",
                "reason": "max_samples_reached",
                "today": today,
                "n_today": n_today,
                "max_samples": max_samples,
            })
            raise SystemExit(f"Replay GateScore sampling blocked: max samples reached today ({n_today}/{max_samples})")

    # If we got here: allow
    _append_arm_event(logs, {
        "ts_utc": now_utc.isoformat(),
        "action": "allow",
        "until_utc": until_dt.isoformat(),
        "max_samples": max_samples,
    })

    # ------------------------------------------------------------
    # FAIL-CLOSED DEFAULTS
    # ------------------------------------------------------------
    score = 0.0
    count_signals = 0
    pnl_samples = 0

    try:
        import hybrid_ai_trading.replay.nvda_bplus_gate_score as gs
        score = float(gs.compute_nvda_gatescore_today(repo_root))
        count_signals = int(getattr(gs, "_NVDA_GS_COUNT_SIGNALS", 1))
        pnl_samples = int(getattr(gs, "_NVDA_GS_PNL_SAMPLES", 1))
    except Exception:
        # remain fail-closed
        pass

    # ------------------------------------------------------------
    # APPEND-SAFE WRITE
    # ------------------------------------------------------------
    need_header = not out.exists()
    mode = "a" if out.exists() else "w"

    with out.open(mode, encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if need_header:
            w.writerow(["as_of_date", "score", "count_signals", "pnl_samples"])
        w.writerow([today, f"{score:.6f}", count_signals, pnl_samples])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

