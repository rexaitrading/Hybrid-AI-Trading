from __future__ import annotations

import json
import pathlib
import os

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

    mp = get_last_prices(symbols=symbols, client_id=getattr(args, "client_id", 3021))
    if not isinstance(mp, dict):
        raise RuntimeError("ib_snapshot_helper_bad_return: expected dict")

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
def main(argv=None) -> int:
    _chdir_repo_root()
    args = parse_args(argv)

    # Hard enforce paper mode for anything downstream
    os.environ["HAT_IS_PAPER"] = "1"

    cfg: Dict[str, Any] = load_config(args.config)

    # Universe
    symbols = list(getattr(args, "universe_list", []) or [])
    if not symbols:
        # fall back to parser default if something went wrong
        u = getattr(args, "universe", "") or ""
        symbols = [s.strip().upper() for s in u.split(",") if s.strip()]

    # Diagnostics
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
    print("[PaperRunner] args:", json.dumps(info, ensure_ascii=False))

    # Build risk manager (Phase-6 step)
    try:
        risk_mgr = _build_risk_mgr(cfg)
    except Exception as e:
        print(f"[PaperRunner] ERROR risk_mgr: {e!r}")
        return 2

    # One tick (safe) or small loop
    def do_tick() -> int:
        # Choose price source (Phase-6 enhancement)
        use_ib = bool(getattr(args, "ib_snapshots", False)) and (not bool(getattr(args, "provider_only", False)))
        if use_ib:
            if not _market_open_allowed(args):
                raise RuntimeError("ib_snapshots_denied: market_closed (use --snapshots-when-closed to override)")
            price_map = _build_ib_snapshot_price_map(symbols, args)
        else:
            price_map = _build_provider_price_map(symbols, cfg, args)

        try:
            out = qc.run_once(symbols, price_map, risk_mgr)
        except Exception as e:
            rec = {
                "ts_utc": iso_utc_now(),
                "status": "error",
                "error": repr(e),
                "symbols": symbols,
                "price_map": price_map,
            }
            if args.log_file:
                _append_jsonl(args.log_file, rec)
            print("[PaperRunner] tick ERROR:", json.dumps(rec, ensure_ascii=False))
            return 3

        rec = {
            "ts_utc": iso_utc_now(),
            "status": "ok",
            "symbols": symbols,
            "price_map": price_map,
            "result": out,
        }
        if args.log_file:
            _append_jsonl(args.log_file, rec)
        print("[PaperRunner] tick OK:", json.dumps({"status": "ok", "symbols": symbols}, ensure_ascii=False))
        return 0

    if args.once:
        return do_tick()

    # Default: 3 ticks (safe)
    for i in range(3):
        print(f"[PaperRunner] tick {i+1}")
        rc = do_tick()
        if rc != 0:
            return rc
        time.sleep(0.1)

    print("[PaperRunner] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
