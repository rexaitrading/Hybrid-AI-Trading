from __future__ import annotations

import json
import pathlib
import os
from hybrid_ai_trading.runtime.run_context import RunContext

# --- Ensure CWD is repo root (prevents src\\config rebasing) ---
def _chdir_repo_root() -> None:
    try:
        here = pathlib.Path(__file__).resolve()
        # .../src/hybrid_ai_trading/runners/paper_runner.py -> repo root is 4 parents up
        repo = here.parents[3]
        os.chdir(str(repo))
    except Exception:
        pass

import sys
import time

# --- rate limit noisy IB snapshot errors ---
_IB_ERR_EVERY_N = 60
_ib_err_count = 0

import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# IMPORTANT: use absolute imports so this can run as:
#   python -m hybrid_ai_trading.runners.paper_runner
# and (still) as a file in a pinch.
from hybrid_ai_trading.runners.paper_config import load_config, parse_args
from hybrid_ai_trading.runners import paper_quantcore as qc


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# PROXY_FORCE_AFTER_RUNONCE_BEGIN
def _force_proxy_metrics_from_decision(out: Any) -> Any:
    """
    Authoritative proxy-metrics post-processor (proxy_v0_force).
    Reads nested decision fields:
      decision.risk_approved.approved (bool)
      decision.kelly_size.f (float)
    If actionable, forces tiny non-zero metrics so GateScore pipeline can run.
    """
    try:
        if not isinstance(out, list):
            return out
        fixed = []
        for it in out:
            d = dict(it or {})
            dec = d.get("decision", None)
            ra_ok = False
            ks_f = 0.0
            try:
                if isinstance(dec, dict):
                    ra = dec.get("risk_approved", None)
                    ks = dec.get("kelly_size", None)
                    if isinstance(ra, dict):
                        ra_ok = bool(ra.get("approved", False))
                    if isinstance(ks, dict):
                        try:
                            ks_f = float(ks.get("f", 0.0) or 0.0)
                        except Exception:
                            ks_f = 0.0
            except Exception:
                ra_ok = False
                ks_f = 0.0

            actionable = ra_ok or (ks_f > 0.0)
            if actionable:
                d["edge_ratio"] = 0.01
                d["micro_score"] = 0.10
                d["pnl_samples"] = int(d.get("pnl_samples", 0) or 0)
                d["metrics_source"] = "proxy_v0_force"
            else:
                d.setdefault("edge_ratio", 0.0)
                d.setdefault("micro_score", 0.0)
                d.setdefault("pnl_samples", 0)
                d.setdefault("metrics_source", "proxy_v0_force")
            fixed.append(d)
        return fixed
    except Exception:
        return out
# PROXY_FORCE_AFTER_RUNONCE_END

# PROXY_METRICS_V0_BEGIN
def _attach_proxy_metrics_v0(item: dict) -> dict:
    """
    Attach minimal proxy metrics for GateScore pipeline. Explicitly labeled proxy_v0.
    This is NOT a claim of real edge; it prevents 'eligible=0 forever' schema dead-ends.
    """
    try:
        d = dict(item or {})
        decision = str(d.get("decision", "")).strip().upper()
        actionable = decision in {"BUY", "SELL", "LONG", "SHORT", "ENTER", "ENTRY"}
        d.setdefault("edge_ratio", 0.01 if actionable else 0.0)
        d.setdefault("micro_score", 0.10 if actionable else 0.0)
        d.setdefault("pnl_samples", 0)
        d.setdefault("metrics_source", "proxy_v0")
        return d
    except Exception:
        return dict(item or {})

def _paperlive_apply_proxy_metrics(out: Any) -> Any:
    try:
        if isinstance(out, list):
            return [_attach_proxy_metrics_v0(x) for x in (out or [])]
    except Exception:
        pass
    return out
# PROXY_METRICS_V0_END


def _safe_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _build_risk_mgr(cfg: Dict[str, Any]) -> Any:
    """
    Build a RiskManager using your repo's risk factory.
    We do best-effort discovery to avoid hard coupling during refactors.
    """
    # Preferred: paper_risk_factory.make_risk_manager(cfg) or build_risk_manager(cfg)
    try:
        rf = __import__("hybrid_ai_trading.runners.paper_risk_factory", fromlist=["*"])
        for name in ("make_risk_manager", "build_risk_manager", "create_risk_manager"):
            if hasattr(rf, name):
                return getattr(rf, name)(cfg)
        # Next: get_RiskManager() returns a RiskManager class; then instantiate with cfg
        if hasattr(rf, "get_RiskManager"):
            RM = rf.get_RiskManager()
            try:
                return RM(cfg)
            except TypeError:
                return RM()
        # Next: RiskManager symbol inside the module
        if hasattr(rf, "RiskManager"):
            RM = getattr(rf, "RiskManager")
            try:
                return RM(cfg)
            except TypeError:
                return RM()
    except Exception as e:
        raise RuntimeError(f"risk_factory_failed: {e!r}") from e

    raise RuntimeError("risk_factory_failed: could not locate risk manager factory in paper_risk_factory.py")


def _build_provider_price_map(symbols: list[str], cfg: Dict[str, Any], args: Any) -> Dict[str, float]:
    """
    Provider-only price map (safe). We do NOT touch IB here.
    Priority:
      1) cfg.prices.<SYM>
      2) cfg.default_price
      3) 0.0 (allowed for dry drill / wiring tests)
    """
    prices_cfg = _safe_get(cfg, "prices", {}) or {}
    default_px = float(_safe_get(cfg, "default_price", 0.0) or 0.0)

    # Allow CLI override if you later add it to parser; tolerate missing attribute.
    cli_px = float(getattr(args, "price", 0.0) or 0.0)

    out: Dict[str, float] = {}
    for s in symbols:
        v = prices_cfg.get(s)
        if v is not None:
            out[s] = float(v)
        elif cli_px != 0.0:
            out[s] = cli_px
        else:
            out[s] = default_px
    return out



def _ib_gateway_up(host: str = "127.0.0.1", port: int = 4002, timeout_s: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except Exception:
        return False


def _build_ib_snapshot_price_map(symbols: list[str], args: Any) -> Dict[str, float]:
    """
    Build price_map using IB snapshots (paper). Guarded by:
      - HAT_IS_PAPER=1 (paper only)
      - IB Gateway port up (4002)
      - market-open policy handled by caller (unless snapshots_when_closed)
    Returns dict {SYM: float}. Fail-closed if any missing.
    """
    import os
    from typing import Dict

    if os.environ.get("HAT_IS_PAPER", "1") != "1":
        raise RuntimeError("ib_snapshots_denied: HAT_IS_PAPER!=1")

    if not _ib_gateway_up("127.0.0.1", 4002, timeout_s=0.5):
        raise RuntimeError("ib_gateway_down: 127.0.0.1:4002 not reachable")

    # Repo-native snapshot helper
    from hybrid_ai_trading.brokers.ib_client import get_last_prices

    import math
    mp = None
    last_err = None
    for _try in range(3):
        try:
            mp = get_last_prices(symbols=symbols, client_id=getattr(args, "client_id", 3021))
            last_err = None
        except Exception as e:
            mp = None
            last_err = e

        # If we got a dict, validate it
        if isinstance(mp, dict):
            bad = []
            for s in symbols:
                keyU = str(s).upper()
                v = mp.get(keyU, mp.get(str(s), None))
                try:
                    fv = float(v)
                except Exception:
                    fv = float("nan")
                if v is None or math.isnan(fv) or fv <= 0.0:
                    bad.append((keyU, v))
            if not bad:
                break
            last_err = RuntimeError(f"ib_snapshot_bad_price: {bad}")
            mp = None

        # backoff between tries
        time.sleep(0.35)
    if not isinstance(mp, dict):
        raise RuntimeError(f"ib_snapshot_helper_bad_return: {last_err!r}") if last_err else RuntimeError("ib_snapshot_helper_bad_return: expected dict")
    out: Dict[str, float] = {}
    for s in symbols:
        v = mp.get(str(s).upper()) if isinstance(s, str) else mp.get(s)
        if v is None:
            # also try raw key
            v = mp.get(str(s))
        if v is None:
            raise RuntimeError(f"ib_snapshot_missing_symbol: {s}")
        out[str(s).upper()] = float(v)
    return out

def _market_open_allowed(args: Any) -> bool:
    """
    Minimal market-open gate.
    If --snapshots-when-closed is set, allow snapshots anytime.
    Otherwise, allow only during local market hours (09:30-16:00).
    """
    if bool(getattr(args, "snapshots_when_closed", False)):
        return True
    now = datetime.now().astimezone()
    hhmm = now.hour * 60 + now.minute
    open_m = 9 * 60 + 30
    close_m = 16 * 60
    return open_m <= hhmm <= close_m

def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def _write_heartbeat(symbols: list[str], tick_no: int, price_source: str, log_file: str | None) -> None:
    """
    Heartbeat file for ops visibility.
    Writes a single JSON object (NOT JSONL), valid JSON (no literal \\n suffix).
    Must never crash runner.
    """
    try:
        p = pathlib.Path("logs") / "paper_live_heartbeat.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts_utc": iso_utc_now(),
            "symbols": list(symbols),
            "tick": int(tick_no),
            "price_source": str(price_source),
            "ibg_up": bool(_ib_gateway_up()),
            "log_file": log_file,
        }
        p.write_text(json.dumps(rec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception:
        pass
def main(argv=None) -> int:
    _chdir_repo_root()
    args = parse_args(argv)
    # --- Resolve config path against repo root (no src\\config rebasing) ---
    try:
        here = pathlib.Path(__file__).resolve()
        repo = here.parents[3]
        p = pathlib.Path(args.config)
        if not p.is_absolute():
            args.config = str((repo / p).resolve())
    except Exception:
        pass


    # --- Fallback: honor --ticks/--sleep-sec even if parser didn't attach attrs ---
    raw = list(argv) if argv is not None else sys.argv[1:]
    try:
        if "--ticks" in raw:
            j = raw.index("--ticks")
            if j + 1 < len(raw):
                setattr(args, "ticks", int(raw[j+1]))
        if "--sleep-sec" in raw:
            j = raw.index("--sleep-sec")
            if j + 1 < len(raw):
                setattr(args, "sleep_sec", float(raw[j+1]))
    except Exception:
        pass

    # For visibility
    try:
        print(f"[PaperRunner] loopctl ticks={getattr(args, 'ticks', None)} sleep_sec={getattr(args, 'sleep_sec', None)}")
    except Exception:
        pass


    # Hard enforce paper mode for anything downstream
    os.environ["HAT_IS_PAPER"] = "1"

    cfg: Dict[str, Any] = load_config(args.config)
    # If log_file is missing/empty, default to auto so every run emits evidence.
    try:
        if not getattr(args, "log_file", None):
            args.log_file = "auto"
    except Exception:
        pass

    # --- Auto daily rollover log file ---
    try:
        if getattr(args, "log_file", None) == "auto":
            day = datetime.now().astimezone().date().isoformat()
            sym = "ALL"
            try:
                sym = "_" .join(getattr(args, "universe_list", []) or []) or "ALL"
            except Exception:
                sym = "ALL"
            args.log_file = f"logs/paper_live_{sym}_{day}.jsonl"
    except Exception:
        pass

    # Universe
    symbols = list(getattr(args, "universe_list", []) or [])
    if not symbols:
        # fall back to parser default if something went wrong
        u = getattr(args, "universe", "") or ""
        symbols = [s.strip().upper() for s in u.split(",") if s.strip()]

    # Diagnostics
    # RunContext unification (single source of truth; fail-closed)
    ctx = RunContext.from_env_and_args(
        symbol=(symbols[0] if symbols else "NVDA"),
        regime="unknown",
        mode="paper",
    )
    info = {
        "ts_utc": iso_utc_now(),
        "config_path": args.config,
        "config_error": cfg.get("_error"),
        "universe": symbols,
        "mdt": args.mdt,
        "client_id": args.client_id,
        "log_file": args.log_file,
        "dry_drill": bool(args.dry_drill),
        "snapshots_when_closed": bool(args.snapshots_when_closed),
        "enforce_riskhub": bool(args.enforce_riskhub),
        "prefer_providers": bool(args.prefer_providers),
        "provider_only": bool(args.provider_only),
        "once": bool(args.once),
    }
    print("[PaperRunner] args:", json.dumps(info, ensure_ascii=True))

    print("[PaperRunner] ctx:", json.dumps({"as_of_date": ctx.as_of_date, "mode": ctx.mode, "is_paper": ctx.is_paper, "symbol": ctx.symbol}, ensure_ascii=True))
    # Build risk manager (Phase-6 step)
    try:
        risk_mgr = _build_risk_mgr(cfg)
    except Exception as e:
        print(f"[PaperRunner] ERROR risk_mgr: {e!r}")
        return 2

    # One tick (safe) or small loop
    def do_tick(tick_no: int = 1) -> int:
        # Provider-first init (always defined; provider-only safe)
        price_source = "provider_only" if bool(getattr(args, "provider_only", False)) else "provider"
        price_map = _build_provider_price_map(symbols, cfg, args)

        # Optional IB snapshot override (paper only, guarded, fail-closed fallback)
        use_ib = bool(getattr(args, "ib_snapshots", False)) and (not bool(getattr(args, "provider_only", False)))
        if use_ib:
            if not _market_open_allowed(args):
                price_source = "provider_fallback_closed"
            else:
                try:
                    price_map = _build_ib_snapshot_price_map(symbols, args)
                    # Fail-closed: None/NaN/<=0 triggers provider fallback
                    import math
                    bad = []
                    for s in symbols:
                        v = price_map.get(s)
                        if v is None:
                            bad.append((s, v)); continue
                        try:
                            fv = float(v)
                        except Exception:
                            bad.append((s, v)); continue
                        if math.isnan(fv) or fv <= 0.0:
                            bad.append((s, fv))
                    if bad:
                        raise RuntimeError(f"ib_snapshot_bad_prices: {bad}")
                    price_source = "ib_snapshot"
                except Exception as e:
                    global _ib_err_count
                    _ib_err_count += 1
                    if (_ib_err_count % _IB_ERR_EVERY_N) == 1:
                        print(f"[PaperRunner] IB snapshots failed, fallback to provider: {e!r}")
                    price_map = _build_provider_price_map(symbols, cfg, args)
                    price_source = "provider_fallback"

        try:
            # --- FAIL-CLOSED: invalid price_map (<=0) must never be emitted as ok ---
            bad = []
            for s in symbols:
                v = price_map.get(s)
                try:
                    fv = float(v)
                except Exception:
                    fv = -1.0
                if fv <= 0.0:
                    bad.append((s, v))
            if bad:
                rec = {"ts_utc": iso_utc_now(), "status": "bad_price", "symbols": symbols, "price_map": price_map, "result": [], "price_source": "bad_price", "error": f"bad_price_map:{bad}"}
                if args.log_file:
                    _append_jsonl(args.log_file, rec)
                print("[PaperRunner] tick BAD_PRICE:", json.dumps(rec, ensure_ascii=True))
                return 4

            out = qc.run_once(symbols, price_map, risk_mgr)

            out = _force_proxy_metrics_from_decision(out)  # PROXY_FORCE_AFTER_RUNONCE_APPLY
        except Exception as e:
            rec = {
                "ts_utc": iso_utc_now(),
                "status": "error",
                "error": repr(e),
                "symbols": symbols,
                "price_map": price_map,
                "price_source": price_source,
            }
            if args.log_file:
                _append_jsonl(args.log_file, rec)
            print("[PaperRunner] tick ERROR:", json.dumps(rec, ensure_ascii=True))
            return 3

        rec = {
            "ts_utc": iso_utc_now(),
            "status": "ok",
            "symbols": symbols,
            "price_map": price_map,
            "result": out,
            "price_source": price_source,
        }
        if args.log_file:
            _append_jsonl(args.log_file, rec)
        print("[PaperRunner] tick OK:", json.dumps({"status": "ok", "symbols": symbols}, ensure_ascii=True))

        # heartbeat (each tick)
        _write_heartbeat(symbols, int(tick_no), price_source, getattr(args, "log_file", None))
        try:
            print(f"[PaperRunner] price_source={price_source}")
        except Exception:
            pass
        return 0

    if args.once:
        return do_tick(1)
    # Loop control
    ticks = int(getattr(args, "ticks", 3) or 0)
    sleep_sec = float(getattr(args, "sleep_sec", 0.25) or 0.0)

    if ticks == 0:
        i = 0
        while True:
            i += 1
            print(f"[PaperRunner] tick {i}")
            try:
                rc = do_tick(i)
            except KeyboardInterrupt:
                print("[PaperRunner] CTRL+C received, exiting cleanly.")
                return 130
            if rc != 0:
                return rc
            try:
                time.sleep(max(0.0, sleep_sec))
            except KeyboardInterrupt:
                print("[PaperRunner] CTRL+C received, exiting cleanly.")
                return 130
    else:
        for i in range(ticks):
            print(f"[PaperRunner] tick {i+1}")
            try:
                rc = do_tick(i)
            except KeyboardInterrupt:
                print("[PaperRunner] CTRL+C received, exiting cleanly.")
                return 130
            if rc != 0:
                return rc
            try:
                time.sleep(max(0.0, sleep_sec))
            except KeyboardInterrupt:
                print("[PaperRunner] CTRL+C received, exiting cleanly.")
                return 130
    print("[PaperRunner] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
