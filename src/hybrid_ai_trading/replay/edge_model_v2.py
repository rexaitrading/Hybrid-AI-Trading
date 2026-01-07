from __future__ import annotations

# --- TZ_IMPORT_GUARD_BEGIN ---
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception as _e:
    ZoneInfo = None  # type: ignore
    raise RuntimeError(f"FAIL-CLOSED: ZoneInfo import failed: {_e}")
# --- TZ_IMPORT_GUARD_END ---
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hybrid_ai_trading.replay.edge_model_v0 import Bar, read_bars_csv, vwap_series, gen_bplus_signals


def _parse_ts(ts: str) -> Optional[datetime]:
    ts = (ts or "").strip()
    if not ts:
        return None
    try:
        # IB format in logs/bars: "YYYYMMDD␠␠HH:MM:SS" (TWO spaces)
        if len(ts) >= 17 and ts[8:10] == "  ":
            return datetime.strptime(ts[:17], "%Y%m%d  %H:%M:%S")

        # Also accept collapsed-space variant: "YYYYMMDD HH:MM:SS"
        if len(ts) >= 17 and ts[8] == " " and ts[11] == ":":
            return datetime.strptime(ts[:17], "%Y%m%d %H:%M:%S")

        # ISO fallback (strip trailing Z)
        s = ts.replace("Z", "")
        return datetime.fromisoformat(s)
    except Exception:
        return None
def _rth_mask(bars: List[Bar]) -> List[bool]:
    """
    RTH: 09:30–16:00 America/New_York.
    IBKR timestamps may be exchange-local OR UTC-stamped.
    We auto-detect by picking the interpretation that yields the most RTH minutes.
    """
    ny = ZoneInfo("America/New_York")
    sys_tz = datetime.now().astimezone().tzinfo or timezone.utc
    parsed: List[Optional[datetime]] = []
    for b in bars:
        parsed.append(_parse_ts(b.ts))

    # Candidate A: treat naive dt as NY-local
    def _count_rth_local() -> int:
        seen = set()
        for dt in parsed:
            if dt is None:
                continue
            # if tz-aware, convert to NY; else treat as NY
            dtny = dt.astimezone(ny) if dt.tzinfo else dt.replace(tzinfo=sys_tz).astimezone(ny)
            m = dtny.hour * 60 + dtny.minute
            if (9 * 60 + 30) <= m <= (15 * 60 + 59):
                seen.add((dtny.hour, dtny.minute))
        return len(seen)

    # Candidate B: treat naive dt as UTC then convert to NY
    def _count_rth_utc2ny() -> int:
        seen = set()
        for dt in parsed:
            if dt is None:
                continue
            dtutc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            dtny = dtutc.astimezone(ny)
            m = dtny.hour * 60 + dtny.minute
            if (9 * 60 + 30) <= m <= (15 * 60 + 59):
                seen.add((dtny.hour, dtny.minute))
        return len(seen)

    c_local = _count_rth_local()
    c_utc2ny = _count_rth_utc2ny()

    use_utc2ny = (c_utc2ny > c_local)

    out: List[bool] = []
    for dt in parsed:
        if dt is None:
            out.append(False)
            continue
        if use_utc2ny:
            dtutc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            dtny = dtutc.astimezone(ny)
        else:
            dtny = dt.astimezone(ny) if dt.tzinfo else dt.replace(tzinfo=sys_tz).astimezone(ny)
        hhmm = dtny.hour * 60 + dtny.minute
        out.append(hhmm >= (9 * 60 + 30) and hhmm <= (16 * 60))
    return out
def _atr(bars: List[Bar], mask: List[bool], n: int = 14) -> float:
    # ATR on RTH bars only (simple, stable)
    trs: List[float] = []
    prev_c: Optional[float] = None
    for b, ok in zip(bars, mask):
        if not ok:
            continue
        if prev_c is None:
            prev_c = b.c
            continue
        tr = max(b.h - b.l, abs(b.h - prev_c), abs(b.l - prev_c))
        trs.append(tr)
        prev_c = b.c
    if len(trs) < max(3, n):
        return max(0.10, (sum(trs) / max(1, len(trs))) if trs else 0.10)
    return max(0.10, sum(trs[-n:]) / float(n))


def score_signals_v2(
    bars: List[Bar],
    signal_idx: List[int],
    risk_unit_usd: float = 100.0,
    fee_per_trade_usd: float = 0.35,
    slip_bps: float = 1.5,
    atr_n: int = 14,
    atr_mult: float = 1.0,
    r_mult_tp: float = 1.2,
    time_stop_bars: int = 45,
    max_shares: int = 500,
) -> List[Dict]:
    """
    Edge realism v2:
      - RTH-only evaluation (signals outside RTH ignored)
      - ORB breakout uses gen_bplus_signals (v0) but we require RTH mask true
      - entry is NEXT BAR open (not same-bar close)
      - stop distance = max(ATR*mult, 0.10)
      - exit: stop/target intrabar, VWAP fail, or time stop
      - costs: slippage+fees
    """
    events: List[Dict] = []
    if not bars or not signal_idx:
        return events

    rth = _rth_mask(bars)
    vw = vwap_series(bars)
    atr = _atr(bars, rth, n=atr_n)
    stop_dist = max(0.10, atr * max(0.1, atr_mult))

    for i in signal_idx:
        # require signal bar in RTH and have a next bar in RTH
        if i + 1 >= len(bars):
            continue
        if not rth[i] or not rth[i + 1]:
            continue

        entry = bars[i + 1].o  # next-bar open fill
        stop = entry - stop_dist
        tgt = entry + (r_mult_tp * stop_dist)

        shares = int(max(1.0, min(float(max_shares), (risk_unit_usd / max(1e-9, stop_dist)))))

        j_end = min(len(bars) - 1, (i + 1) + max(1, time_stop_bars))
        exit_px: Optional[float] = None

        for j in range(i + 2, j_end + 1):
            if not rth[j]:
                continue
            if bars[j].l <= stop:
                exit_px = stop
                break
            if bars[j].h >= tgt:
                exit_px = tgt
                break
            if bars[j].c < vw[j]:
                exit_px = bars[j].c
                break

        if exit_px is None:
            # last available RTH close before j_end
            k = j_end
            while k > (i + 1) and not rth[k]:
                k -= 1
            exit_px = bars[k].c

        slip = (entry * (slip_bps / 10000.0)) + (exit_px * (slip_bps / 10000.0))
        fees = 2.0 * fee_per_trade_usd

        gross = (exit_px - entry) * shares
        net = gross - (slip * shares) - fees

        edge_ratio = net / max(1e-9, risk_unit_usd)
        micro_cost = ((slip * shares) + fees) / max(1e-9, risk_unit_usd)
        micro_score = max(0.0, min(1.0, 1.0 - micro_cost))

        events.append(
            {
                "count_signals": 1,
                "pnl_samples": 1,
                "realized_pnl": float(net),
                "edge_ratio": float(edge_ratio),
                "micro_score": float(micro_score),
                "edge_source": "edge_model_v2",
                "micro_score_source": "edge_model_v2",
            }
        )

    return events
