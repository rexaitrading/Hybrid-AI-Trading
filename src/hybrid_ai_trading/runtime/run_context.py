from __future__ import annotations

from dataclasses import dataclass
from .blockg_types import load_blockg_status
from .blockg_types import BlockGStatus, load_blockg_status
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional


class RunMode(str, Enum):
    PREMARKET = "premarket"
    PAPER     = "paper"
    LIVE      = "live"
    NOTION    = "notion"


@dataclass(frozen=True)
class RunContext:
    """
    Immutable runtime context for a single system run.

    This object is the *only* authority for:
    - run mode (paper/live/etc.)
    - trading date
    - symbol scope
    - safety readiness snapshots
    """

    mode: RunMode
    trading_date: date

    # scope
    symbol: Optional[str] = None  # NVDA / SPY / QQQ / None (ALL)

    # safety snapshots
    phase4_passed: bool = False
    blockg_ready: bool = False

    # Phase-1A: additional safety flags (defaults fail-safe)
    phase23_ok: bool = False
    ev_hard_ok: bool = False
    gatescore_fresh: bool = False
    # io roots
    repo_root: Path = Path(".")
    logs_dir: Path = Path("logs")

    @property
    def is_live(self) -> bool:
        return self.mode == RunMode.LIVE

    @property
    def is_paper(self) -> bool:
        return self.mode == RunMode.PAPER

    @property
    def is_premarket(self) -> bool:
        return self.mode == RunMode.PREMARKET
    def norm_symbol(self) -> Optional[str]:
        """Return normalized symbol (upper/trim) or None."""
        if self.symbol is None:
            return None
        s = str(self.symbol).strip().upper()
        return s if s else None

    def require_live_safe(self) -> None:
        """
        Hard safety assertion for LIVE mode (fail-closed).

        Phase-1C rule:
          LIVE requires: Phase4 + BlockG + Phase23 + EV-hard + GateScore freshness.
        """
        if not self.is_live:
            return
        if not self.phase4_passed:
            raise RuntimeError("RunContext: Phase-4 not passed for LIVE run")
        if not self.blockg_ready:
            raise RuntimeError("RunContext: Block-G not ready for LIVE run")
        if not getattr(self, "phase23_ok", False):
            raise RuntimeError("RunContext: Phase23 health not OK for LIVE run")
        if not getattr(self, "ev_hard_ok", False):
            raise RuntimeError("RunContext: EV-hard daily not OK for LIVE run")
        if not getattr(self, "gatescore_fresh", False):
            raise RuntimeError("RunContext: GateScore not fresh/valid for LIVE run")



def load_default_run_context(
    mode: "RunMode | str",
    symbol: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> RunContext:
    """
    Load a RunContext using logs/blockg_status_stub.json (typed mirror).

    - Keeps RunContext as the canonical in-process authority.
    - Hydrates Block-G derived flags fail-closed.
    """
    # Normalize mode into RunMode
    m = mode
    if isinstance(mode, str):
        m_low = mode.strip().lower()
        try:
            m = RunMode(m_low)
        except Exception:
            # allow "LIVE"/"PAPER"/"PREMARKET" style strings
            if "live" in m_low:
                m = RunMode.LIVE
            elif "paper" in m_low:
                m = RunMode.PAPER
            elif "premarket" in m_low:
                m = RunMode.PREMARKET
            else:
                m = RunMode.PREMARKET

    root = repo_root or Path(__file__).resolve().parents[3]
    logs_dir = root / "logs"
    stub = logs_dir / "blockg_status_stub.json"

    b = load_blockg_status(stub)

    # Map JSON → RunContext safety flags (fail-closed)
    sym = (symbol or "").strip().upper() or None

    # per-symbol ready flag
    per_symbol_ready = False
    if sym == "NVDA":
        per_symbol_ready = bool(b.nvda_blockg_ready)
    elif sym == "SPY":
        per_symbol_ready = bool(b.spy_blockg_ready)
    elif sym == "QQQ":
        per_symbol_ready = bool(b.qqq_blockg_ready)
    else:
        # If symbol not specified, stay strict: require gatescore_ok_today AND at least one symbol is ready.
        per_symbol_ready = bool(b.gatescore_ok_today) and (bool(b.nvda_blockg_ready) or bool(b.spy_blockg_ready) or bool(b.qqq_blockg_ready))

    ctx = RunContext(
        mode=m,
        trading_date=date.today(),
        symbol=sym,
        phase4_passed=bool(b.phase4_ok_today),
        blockg_ready=bool(per_symbol_ready),
        phase23_ok=bool(b.phase23_health_ok_today),
        ev_hard_ok=bool(b.ev_hard_daily_ok_today),
        gatescore_fresh=bool(b.gatescore_fresh_today),
        repo_root=root,
        logs_dir=logs_dir,
    )
    return ctx