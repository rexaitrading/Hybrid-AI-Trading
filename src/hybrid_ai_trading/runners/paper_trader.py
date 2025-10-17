# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
from typing import Optional

from ib_insync import IB  # noqa: F401 (kept for future use)
from hybrid_ai_trading.utils.ib_conn import ib_session
from hybrid_ai_trading.utils.preflight import sanity_probe
from hybrid_ai_trading.runners.paper_utils import apply_mdt
from hybrid_ai_trading.runners.paper_logger import JsonlLogger

# Env toggle: allow drills when market is closed
ALLOW_TRADE_WHEN_CLOSED = os.environ.get("ALLOW_TRADE_WHEN_CLOSED", "0") == "1"

def run_paper_session(args) -> int:
    """
    Entry for paper session:
      1) Preflight (paper-only safety, time window)
      2) Optional drill-only when closed (no second IB connect)
      3) Demo loop (replace with real engine)
    """
    force = bool(ALLOW_TRADE_WHEN_CLOSED or getattr(args, "dry_drill", False))

    # ---- Preflight ----
    probe = sanity_probe(symbol="AAPL", qty=1, cushion=0.10, allow_ext=True, force_when_closed=force)
    if not probe.get("ok"):
        raise RuntimeError(f"Preflight failed: {probe}")

    # Skip in strict mode when closed
    if not probe["session"]["ok_time"] and not force:
        print(f"Market closed ({probe['session']['session']}), skipping trading window.")
        return 0

    logger = JsonlLogger(getattr(args, "log_file", "logs/runner_paper.jsonl"))
    logger.info("preflight", probe=probe)

    # If we FORCED while CLOSED, treat as drill-only and exit before opening a second IB session
    if not probe["session"]["ok_time"] and force:
        logger.info("drill_only", note="market closed; forced preflight ran; skipping second IB session")
        return 0

    # ---- Main session (placeholder loop; wire your engine here) ----
    with ib_session() as ib:
        apply_mdt(ib, getattr(args, "mdt", 3))

        if getattr(args, "once", False):
            logger.info("once_done", note="single pass complete")
            return 0

        for i in range(3):
            time.sleep(0.5)
            logger.info("heartbeat", i=i)

    return 0