from __future__ import annotations
import json
import os
import sys

def _out(**kw) -> None:
    print(json.dumps(kw, ensure_ascii=False))

def main(argv: list[str]) -> int:
    kind = (argv[1] if len(argv) > 1 else "").strip().lower()
    hours_back = int(os.getenv("HAT_INTEL_HOURS_BACK", "24"))
    limit = int(os.getenv("HAT_INTEL_LIMIT", "80"))

    try:
        if kind == "news":
            from hybrid_ai_trading.intel.collectors.collect_news_multi import collect as collect_news
            ok, reason, count = collect_news(hours_back=hours_back, limit_total=limit)
            _out(ok=bool(ok), reason=str(reason), count=int(count), kind="news")
            return 0
        elif kind == "youtube":
            from hybrid_ai_trading.intel.collectors.collect_youtube_rss import collect as collect_yt
            ok, reason, count = collect_yt(hours_back=hours_back, limit_per_feed=max(10, limit))
            _out(ok=bool(ok), reason=str(reason), count=int(count), kind="youtube")
            return 0
        else:
            _out(ok=False, reason="usage: collect_cli.py news|youtube", count=0, kind=kind or "none")
            return 0
    except Exception as e:
        _out(ok=False, reason=f"exception:{type(e).__name__}:{e}", count=0, kind=kind or "none")
        return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
