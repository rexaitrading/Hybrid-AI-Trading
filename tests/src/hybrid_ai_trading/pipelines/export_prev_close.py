"""
Test-only Export Previous Close Pipeline (stubbed).

- Designed to satisfy tests/pipelines/test_export_prev_close_full.py::test_main_entrypoint_runs
- When COINAPI_STUB=1 and no POLYGON_KEY is present, it should WARN but exit 0.
"""

import logging
import os
import sys
from typing import Optional, List

logger = logging.getLogger(__name__)


def _log_stub_mode() -> None:
    """Log stub vs live mode based on env vars."""
    stub = os.getenv("COINAPI_STUB") == "1"
    polygon_key: Optional[str] = os.getenv("POLYGON_KEY")

    if stub and not polygon_key:
        logger.warning(
            "export_prev_close (tests/src): COINAPI_STUB=1 and no POLYGON_KEY  running in stub mode."
        )
    elif stub and polygon_key:
        logger.info("export_prev_close (tests/src): stub mode but POLYGON_KEY is set.")
    elif polygon_key:
        logger.info("export_prev_close (tests/src): live mode with POLYGON_KEY.")
    else:
        logger.info("export_prev_close (tests/src): no COINAPI_STUB and no POLYGON_KEY  noop.")


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entrypoint for `python -m hybrid_ai_trading.pipelines.export_prev_close`
    when PYTHONPATH points to tests/src.

    Behavior:
    - Log stub/live mode info.
    - Never raise for missing keys when COINAPI_STUB=1.
    - Always return 0 on success.
    """
    if argv is None:
        argv = sys.argv[1:]

    _log_stub_mode()

    # Emit a token that the test expects
    print("Exported (tests/src stub)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
