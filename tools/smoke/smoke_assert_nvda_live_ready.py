import os, sys
from hybrid_ai_trading.execution.blockg_contract import assert_nvda_live_ready

def main() -> int:
    if not os.environ.get("HAT_BLOCKG_STATUS_PATH","").strip():
        print("MISSING_ENV HAT_BLOCKG_STATUS_PATH", file=sys.stderr)
        return 3
    try:
        assert_nvda_live_ready()
        print("UNEXPECTED_READY")
        return 99
    except Exception as e:
        print("EXPECTED_BLOCK", type(e).__name__, str(e)[:260])
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
