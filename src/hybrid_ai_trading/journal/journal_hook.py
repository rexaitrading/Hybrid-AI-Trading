from __future__ import annotations

import datetime
import os
import subprocess
from typing import Optional, Sequence

# repo root: .../src/hybrid_ai_trading/journal -> ../../../
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PS = os.path.join(ROOT, "scripts", "journal", "Write-Trade.ps1")


def _ps_args(args: Sequence[str]) -> Sequence[str]:
    return [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        PS,
        *args,
    ]


def enabled() -> bool:
    return os.environ.get("HAT_JOURNAL_ENABLE") == "1"


def _fmt(x: Optional[float]) -> Optional[str]:
    return None if x is None else f"{float(x)}"


def journal_entry_open(
    symbol: str,
    qty: float,
    entry_px: float,
    side: str = "BUY",
    session_id: Optional[str] = None,
    kelly_f: Optional[float] = None,
    risk_usd: Optional[float] = None,
    regime: Optional[str] = None,
    sentiment: Optional[str] = None,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    ts: Optional[datetime.datetime] = None,
) -> None:
    if not enabled() or not os.path.exists(PS):
        return
    args = [
        "-Title",
        f"{symbol} OPEN {side}",
        "-Symbol",
        symbol,
        "-Side",
        side,
        "-Qty",
        _fmt(qty) or "0",
        "-EntryPx",
        _fmt(entry_px) or "0",
        "-Status",
        "Open",
    ]
    if session_id:
        args += ["-SessionId", session_id]
    if kelly_f is not None:
        args += ["-KellyF", _fmt(kelly_f)]
    if risk_usd is not None:
        args += ["-RiskUsd", _fmt(risk_usd)]
    if regime:
        args += ["-Regime", regime]
    if sentiment:
        args += ["-Sentiment", sentiment]
    if reason:
        args += ["-Reason", reason]
    if notes:
        args += ["-Notes", notes]
    if ts:
        args += ["-Ts", ts.strftime("%Y-%m-%dT%H:%M:%S")]
    subprocess.run(_ps_args(args), check=False)


def journal_exit_close(
    symbol: str,
    qty: float,
    entry_px: float,
    exit_px: float,
    side: str = "SELL",
    session_id: Optional[str] = None,
    fees: Optional[float] = None,
    slippage: Optional[float] = None,
    kelly_f: Optional[float] = None,
    risk_usd: Optional[float] = None,
    regime: Optional[str] = None,
    sentiment: Optional[str] = None,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    ts: Optional[datetime.datetime] = None,
) -> None:
    if not enabled() or not os.path.exists(PS):
        return
    # Fallback R multiple if OR range not available: 0.2% of price as risk proxy
    den = max(0.01, abs(entry_px) * 0.002)
    r_mult = float((exit_px - entry_px) / den) if den else 0.0
    gross = float((exit_px - entry_px) * qty)
    args = [
        "-Title",
        f"{symbol} CLOSE {side}",
        "-Symbol",
        symbol,
        "-Side",
        side,
        "-Qty",
        _fmt(qty) or "0",
        "-EntryPx",
        _fmt(entry_px) or "0",
        "-ExitPx",
        _fmt(exit_px) or "0",
        "-Status",
        "Closed",
        "-RMultiple",
        _fmt(r_mult) or "0",
        "-GrossPnl",
        _fmt(gross) or "0",
    ]
    if session_id:
        args += ["-SessionId", session_id]
    if fees is not None:
        args += ["-Fees", _fmt(fees)]
    if slippage is not None:
        args += ["-Slippage", _fmt(slippage)]
    if kelly_f is not None:
        args += ["-KellyF", _fmt(kelly_f)]
    if risk_usd is not None:
        args += ["-RiskUsd", _fmt(risk_usd)]
    if regime:
        args += ["-Regime", regime]
    if sentiment:
        args += ["-Sentiment", sentiment]
    if reason:
        args += ["-Reason", reason]
    if notes:
        args += ["-Notes", notes]
    if ts:
        args += ["-Ts", ts.strftime("%Y-%m-%dT%H:%M:%S")]
    subprocess.run(_ps_args(args), check=False)
