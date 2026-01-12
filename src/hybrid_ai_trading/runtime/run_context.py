from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional
import os


def _envs(name: str) -> str:
    return str(os.environ.get(name, "")).strip()


def _repo_root() -> Path:
    # .../src/hybrid_ai_trading/runtime/run_context.py -> repo root
    return Path(__file__).resolve().parents[3]


def _default_logs_dir(repo_root: Path, market: str) -> Path:
    # Per-market logs root (Phase-5 lane): logs/<MARKET> for non-US; logs/US for US by policy.
    # If tools/Get-MarketLogRoot.ps1 exists, that remains the PowerShell semantic owner.
    m = (market or "US").upper()
    return repo_root / "logs" / m


def _resolve_blockg_status_path(repo_root: Path, market: str) -> Path:
    p_env = _envs("HAT_BLOCKG_STATUS_PATH")
    if p_env:
        return Path(p_env)
    return _default_logs_dir(repo_root, market) / "blockg_status_stub.json"


def _resolve_market(mode: str, env_market: str) -> str:
    # Default US until Asia lane activates.
    m = (env_market or "US").strip().upper()
    return m if m else "US"


def _resolve_market_tz(market: str) -> str:
    # Minimal mapping for A3; Asia lane will extend this.
    m = (market or "US").upper()
    if m == "US":
        return "America/New_York"
    if m == "JP":
        return "Asia/Tokyo"
    if m == "HK":
        return "Asia/Hong_Kong"
    if m == "SG":
        return "Asia/Singapore"
    return "UTC"


def _resolve_broker_profile(mode: str, is_paper: bool) -> str:
    # Keep it simple and explicit (A3).
    if str(mode).lower() == "live" and not is_paper:
        return "IBKR_LIVE"
    return "IBKR_PAPER"


@dataclass(frozen=True)
class RunContext:
    """
    Unified runtime context for all phases.
    Fail-closed defaults:
      - is_paper defaults to True unless mode resolves to "live"
      - market defaults to US
    """
    as_of_date: str
    mode: str                 # "paper" | "live" | "backtest"
    is_paper: bool
    symbol: str
    regime: str

    repo_root: Path
    logs_dir: Path
    blockg_status_path: Path

    # A3 required fields
    market: str
    market_tz: str
    session: str
    calendar_id: str
    broker_profile: str

    @staticmethod
    def from_env() -> "RunContext":
        # Backward-compatible helper.
        v = _envs("HAT_IS_PAPER")
        m = "live" if v == "0" else "paper"
        return RunContext.from_env_and_args(symbol="NVDA", regime="unknown", mode=m)

    @staticmethod
    def today(symbol: str = "NVDA", regime: str = "unknown", is_paper: bool = True, market: str = "US") -> "RunContext":
        root = _repo_root()
        mode = "paper" if bool(is_paper) else "live"
        mk = _resolve_market(mode, market)
        logs = _default_logs_dir(root, mk)
        tz = _resolve_market_tz(mk)
        return RunContext(
            as_of_date=date.today().isoformat(),
            mode=mode,
            is_paper=bool(is_paper),
            symbol=str(symbol),
            regime=str(regime),
            repo_root=root,
            logs_dir=logs,
            blockg_status_path=_resolve_blockg_status_path(root, mk),
            market=mk,
            market_tz=tz,
            session=_envs("HAT_SESSION") or "UNKNOWN",
            calendar_id=_envs("HAT_CALENDAR_ID") or mk,
            broker_profile=_resolve_broker_profile(mode, bool(is_paper)),
        )

    @staticmethod
    def from_env_and_args(
        *,
        symbol: str,
        regime: str,
        mode: Optional[str] = None,
        is_paper: Optional[bool] = None,
        as_of_date: Optional[str] = None,
        repo_root: Optional[Path] = None,
        market: Optional[str] = None,
        market_tz: Optional[str] = None,
        session: Optional[str] = None,
        calendar_id: Optional[str] = None,
        broker_profile: Optional[str] = None,
        logs_dir: Optional[Path] = None,
        blockg_status_path: Optional[Path] = None,
    ) -> "RunContext":
        root = repo_root or _repo_root()

        d = (as_of_date or _envs("HAT_AS_OF_DATE") or date.today().isoformat())
        d = d[:10] if len(d) >= 10 else d

        m0 = (mode or _envs("HAT_MODE").lower())
        if m0 not in ("paper", "live", "backtest"):
            if is_paper is not None:
                m0 = "paper" if bool(is_paper) else "live"
            else:
                env_flag = _envs("HAT_IS_PAPER")
                m0 = "live" if env_flag == "0" else "paper"

        paper = (m0 != "live") if is_paper is None else bool(is_paper)

        mk = _resolve_market(m0, market or _envs("HAT_MARKET"))
        tz = (market_tz or _envs("HAT_MARKET_TZ") or _resolve_market_tz(mk))
        sess = (session or _envs("HAT_SESSION") or "UNKNOWN")
        cal = (calendar_id or _envs("HAT_CALENDAR_ID") or mk)
        bp = (broker_profile or _envs("HAT_BROKER_PROFILE") or _resolve_broker_profile(m0, paper))

        logs = logs_dir or Path(_envs("HAT_LOGS_DIR") or _default_logs_dir(root, mk))
        bgp = blockg_status_path or _resolve_blockg_status_path(root, mk)

        return RunContext(
            as_of_date=d,
            mode=m0,
            is_paper=paper,
            symbol=str(symbol),
            regime=str(regime),
            repo_root=root,
            logs_dir=logs,
            blockg_status_path=bgp,
            market=mk,
            market_tz=tz,
            session=sess,
            calendar_id=cal,
            broker_profile=bp,
        )
