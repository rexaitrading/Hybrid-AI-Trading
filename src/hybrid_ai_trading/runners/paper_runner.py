from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict

from .paper_config import load_config, parse_args


def main(argv=None) -> int:
    args = parse_args(argv)
    cfg: Dict[str, Any] = load_config(args.config)

    # Minimal diagnostics for dry-drill/provider-only and normal paper path
    info = {
        "config_path": args.config,
        "config_error": cfg.get("_error"),
        "universe": getattr(args, "universe_list", []),
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

    # Simulate the "once" cadence without touching IB if provider_only or dry_drill
    if args.once:
        if args.provider_only:
            print("[PaperRunner] provider-only tick (no IB session required).")
        else:
            print(
                "[PaperRunner] IB path requested (ensure Gateway is up on paper port 4002)."
            )
        # artificial throttle honoring mdt (milliseconds per tick if you wish)
        time.sleep(0.1)
        print("[PaperRunner] done.")
        return 0

    # default: loop a couple ticks (safe)
    # --- loop control (institutional: honor --ticks; no hidden caps) ---
    ticks = 300
    sleep_sec = 0.05
    try:
        ticks = int(getattr(args, "ticks", ticks))
    except Exception:
        ticks = 300
    try:
        sleep_sec = float(getattr(args, "sleep_sec", sleep_sec))
    except Exception:
        sleep_sec = 0.05
    n_ticks = 1 if bool(getattr(args, "once", False)) else max(1, ticks)
    print(f"[PaperRunner] loopctl ticks={n_ticks} sleep_sec={sleep_sec}")

    for i in range(n_ticks):
        print(f"[PaperRunner] tick {i+1}")
        time.sleep(0.1)
    print("[PaperRunner] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
