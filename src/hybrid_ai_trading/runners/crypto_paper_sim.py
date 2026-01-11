from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from hybrid_ai_trading.runners.crypto_pricefeed_stub import read_prices_from_json
from hybrid_ai_trading.runners.crypto_state import CryptoSimState, Position, load_state, save_state, local_day
from hybrid_ai_trading.runners.crypto_strategy_simple import SimpleStrategy, Signal


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def jwrite(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def parse_symbols(s: str) -> List[str]:
    parts = [p.strip() for p in (s or "").split(",")]
    return [p for p in parts if p]


def blockg_allow_stub(symbol: str) -> Tuple[bool, str]:
    """
    Paper-sim gate: allow ONLY if HAT_CRYPTO_ALLOW_SIM=1.
    """
    v = os.getenv("HAT_CRYPTO_ALLOW_SIM", "").strip().lower()
    if v in ("1", "true", "yes"):
        return True, "env_override(HAT_CRYPTO_ALLOW_SIM)=true"
    return False, "deny_by_default(no crypto blockg wired)"


def _get_pos(st: CryptoSimState, sym: str) -> Position:
    if sym not in st.pos:
        st.pos[sym] = Position()
    return st.pos[sym]


def _prune_trade_ts(st: CryptoSimState, sym: str, now_ts: float, window_sec: int) -> int:
    arr = st.trades_ts_by_symbol.get(sym, [])
    arr = [t for t in arr if (now_ts - float(t)) <= window_sec]
    st.trades_ts_by_symbol[sym] = arr
    return len(arr)


def _record_trade_ts(st: CryptoSimState, sym: str, now_ts: float) -> None:
    arr = st.trades_ts_by_symbol.get(sym, [])
    arr.append(float(now_ts))
    st.trades_ts_by_symbol[sym] = arr


def risk_allow(
    st: CryptoSimState,
    sym: str,
    daily_loss_cap_usd: float,
    daily_loss_cap_sym_usd: float,
    cooldown_sec: int,
    max_trades_per_hour: int,
) -> Tuple[bool, str]:
    # global daily loss cap
    if st.realized_pnl_usd <= -abs(daily_loss_cap_usd):
        return False, "daily_loss_cap_global"

    # per-symbol daily loss cap
    sym_pnl = float(st.realized_by_symbol.get(sym, 0.0))
    if sym_pnl <= -abs(daily_loss_cap_sym_usd):
        return False, "daily_loss_cap_symbol"

    # cooldown
    arr = st.trades_ts_by_symbol.get(sym, [])
    last_ts = float(arr[-1]) if arr else 0.0
    if last_ts > 0 and (time.time() - last_ts) < cooldown_sec:
        return False, "cooldown"

    # max trades per hour
    now_ts = time.time()
    n = _prune_trade_ts(st, sym, now_ts, 3600)
    if n >= int(max_trades_per_hour):
        return False, "max_trades_per_hour"

    return True, "ok"


def position_value_usd(st: CryptoSimState, sym: str) -> float:
    pos = _get_pos(st, sym)
    px = float(st.last_price.get(sym, 0.0) or 0.0)
    return float(pos.qty) * px


def mark_to_market(st: CryptoSimState) -> None:
    unrl = 0.0
    for sym, pos in st.pos.items():
        px = float(st.last_price.get(sym, 0.0) or 0.0)
        if pos.qty > 0 and px > 0:
            unrl += pos.qty * (px - pos.avg_px)
    st.unrealized_pnl_usd = unrl

    # equity = cash + sum(position market value)
    st.equity_usd = st.cash_usd + sum(
        (p.qty * float(st.last_price.get(s, 0.0) or 0.0)) for s, p in st.pos.items()
    )


def sim_fill(st: CryptoSimState, sym: str, side: str, px: float, usd_notional: float, slip_bps: float) -> dict:
    """
    Simulated market fill with explicit slippage cost accounting.

    - BUY: increases qty, updates avg_px, cash decreases by notional + fee
    - SELL: decreases qty (clamped), realizes pnl on closed qty minus fee
    """
    side = side.upper()
    px = float(px)
    bps = float(max(0.0, slip_bps))
    slip = (bps / 10000.0)

    # fee modeled as slippage * notional (conservative)
    fee_usd = float(usd_notional) * slip

    fill_px = px * (1.0 + slip) if side == "BUY" else px * (1.0 - slip)
    qty_req = float(usd_notional) / fill_px if fill_px > 0 else 0.0

    pos = _get_pos(st, sym)
    before_qty = pos.qty
    before_avg = pos.avg_px

    realized_delta = 0.0
    trade_qty = 0.0

    if side == "BUY":
        trade_qty = qty_req
        new_qty = pos.qty + trade_qty
        if new_qty > 0:
            pos.avg_px = (pos.qty * pos.avg_px + trade_qty * fill_px) / new_qty if pos.qty > 0 else fill_px
        pos.qty = new_qty

        st.cash_usd -= (trade_qty * fill_px)  # equals ~usd_notional
        st.cash_usd -= fee_usd
        st.fees_paid_usd += fee_usd
        st.fees_by_symbol[sym] = float(st.fees_by_symbol.get(sym, 0.0)) + fee_usd
        # Conservative: treat fees as realized drag per symbol so daily symbol cap reflects costs
        st.realized_by_symbol[sym] = float(st.realized_by_symbol.get(sym, 0.0)) - fee_usd

    elif side == "SELL":
        if pos.qty <= 0:
            return {"ok": False, "reason": "sell_no_position"}

        trade_qty = min(pos.qty, qty_req)
        gross = trade_qty * (fill_px - pos.avg_px)
        realized_delta = gross - fee_usd

        pos.qty -= trade_qty
        st.cash_usd += trade_qty * fill_px
        st.cash_usd -= fee_usd

        st.fees_paid_usd += fee_usd
        st.fees_by_symbol[sym] = float(st.fees_by_symbol.get(sym, 0.0)) + fee_usd

        if pos.qty <= 0:
            pos.avg_px = 0.0

        st.realized_pnl_usd += realized_delta
        st.realized_by_symbol[sym] = float(st.realized_by_symbol.get(sym, 0.0)) + realized_delta

    else:
        return {"ok": False, "reason": "bad_side", "side": side}

    st.last_trade_ts = time.time()
    _record_trade_ts(st, sym, st.last_trade_ts)

    return {
        "ok": True,
        "symbol": sym,
        "side": side,
        "fill_px": fill_px,
        "qty": trade_qty,
        "usd_notional": usd_notional,
        "slip_bps": slip_bps,
        "fee_usd": fee_usd,
        "pos_before": {"qty": before_qty, "avg_px": before_avg},
        "pos_after": {"qty": pos.qty, "avg_px": pos.avg_px},
        "realized_pnl_delta": realized_delta,
        "cash_usd": st.cash_usd,
        "realized_pnl_usd": st.realized_pnl_usd,
        "fees_paid_usd": st.fees_paid_usd,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTC-USD,ETH-USD")
    ap.add_argument("--outdir", required=True)

    # execution / risk knobs
    ap.add_argument("--usd_notional", type=float, default=25.0)
    ap.add_argument("--slip_bps", type=float, default=3.0)
    ap.add_argument("--cooldown_sec", type=int, default=60)
    ap.add_argument("--min_hold_sec", type=int, default=15)

    ap.add_argument("--daily_loss_cap", type=float, default=25.0)
    ap.add_argument("--daily_loss_cap_symbol", type=float, default=10.0)

    ap.add_argument("--max_pos_usd", type=float, default=200.0)
    ap.add_argument("--max_trades_per_hour", type=int, default=6)

    # strategy knobs
    ap.add_argument("--lookback", type=int, default=10)
    ap.add_argument("--thr", type=float, default=0.0005)
    ap.add_argument("--dry_run", action="store_true")

    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    day = local_day()
    ev_path = outdir / f"crypto_sim_{day}.jsonl"
    st_path = outdir / "crypto_state.json"
    price_path = outdir / "price_snapshot.json"

    symbols = parse_symbols(args.symbols)
    if not symbols:
        jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "status", "ok": False, "msg": "no symbols"})
        return 2

    st = load_state(st_path)
    if st.day != day:
        st = CryptoSimState(day=day)

    prices = read_prices_from_json(price_path)
    if not prices:
        jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "status", "ok": True, "msg": "no_price_feed_skip"})
        save_state(st_path, st)
        return 0

    strat = SimpleStrategy(lookback=args.lookback, thr=args.thr)

    jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "status", "ok": True, "msg": "tick_start", "symbols": symbols})

    for sym in symbols:
        px = float(prices.get(sym, 0.0) or 0.0)
        if px <= 0:
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "price", "symbol": sym, "ok": False, "reason": "missing_price"})
            continue

        st.last_price[sym] = px

        allow_g, why_g = blockg_allow_stub(sym)
        allow_r, why_r = risk_allow(
            st,
            sym,
            daily_loss_cap_usd=args.daily_loss_cap,
            daily_loss_cap_sym_usd=args.daily_loss_cap_symbol,
            cooldown_sec=args.cooldown_sec,
            max_trades_per_hour=args.max_trades_per_hour,
        )

        sig = strat.on_price_with_hist(sym, px, st.hist)

        # Anti-churn guards:
        pos_qty = _get_pos(st, sym).qty
        # No pyramiding: ignore BUY if already long
        if sig.action == "BUY" and pos_qty > 0:
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "skip", "symbol": sym, "reason": "already_long_no_add"})
            sig = Signal("HOLD", 0.0, "already_long_no_add")

        # Minimum hold time before allowing SELL
        last_ts = 0.0
        arr = st.trades_ts_by_symbol.get(sym, [])
        last_ts = float(arr[-1]) if arr else 0.0
        if sig.action == "SELL" and pos_qty > 0 and last_ts > 0 and (time.time() - last_ts) < int(args.min_hold_sec):
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "skip", "symbol": sym, "reason": "min_hold_sec_block"})
            sig = Signal("HOLD", 0.0, "min_hold_sec_block")

        jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "price", "symbol": sym, "px": px})
        jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "signal", "symbol": sym, "signal": asdict(sig)})
        jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "gate", "symbol": sym, "allow": allow_g, "reason": why_g})
        jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "risk", "symbol": sym, "allow": allow_r, "reason": why_r})


        if args.dry_run:
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "skip", "symbol": sym, "reason": "dry_run_no_trade", "action": sig.action})
            continue



        if not allow_g or not allow_r:
            continue

        # Position cap check (only blocks BUY adds)
        if sig.action == "BUY":
            cur_val = position_value_usd(st, sym)
            if (cur_val + float(args.usd_notional)) > float(args.max_pos_usd):
                jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "skip", "symbol": sym, "reason": "max_pos_usd_cap"})
                continue
            fill = sim_fill(st, sym, "BUY", px, usd_notional=args.usd_notional, slip_bps=args.slip_bps)
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "fill", "symbol": sym, "fill": fill})

        elif sig.action == "SELL":
            if _get_pos(st, sym).qty <= 0:
                jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "skip", "symbol": sym, "reason": "sell_no_position"})
                continue
            fill = sim_fill(st, sym, "SELL", px, usd_notional=args.usd_notional, slip_bps=args.slip_bps)
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "fill", "symbol": sym, "fill": fill})

        else:
            jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "skip", "symbol": sym, "reason": "no_trade_signal", "action": sig.action})
    mark_to_market(st)

    jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "state", "state": {
        "day": st.day,
        "cash_usd": st.cash_usd,
        "equity_usd": st.equity_usd,
        "realized_pnl_usd": st.realized_pnl_usd,
        "unrealized_pnl_usd": st.unrealized_pnl_usd,
        "fees_paid_usd": st.fees_paid_usd,
        "fees_by_symbol": st.fees_by_symbol,
        "realized_by_symbol": st.realized_by_symbol,
        "pos": {k: {"qty": v.qty, "avg_px": v.avg_px} for k, v in st.pos.items()},
    }})

    jwrite(ev_path, {"ts_utc": utc_now_iso(), "kind": "status", "ok": True, "msg": "tick_end"})
    save_state(st_path, st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())








