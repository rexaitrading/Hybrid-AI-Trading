import os
import sys
import time
import traceback
import importlib
import inspect
import argparse
from datetime import datetime, timezone

# Ensure repo root + src are on sys.path
ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ROOT)  # go up from tools/ to repo root
SRC  = os.path.join(ROOT, "src")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] {msg}", flush=True)

def _discover_paper_trader_module() -> str:
    """
    Walk SRC and find paper_trader.py.
    Build a module path like 'hybrid_ai_trading.runners.paper_trader'.
    """
    for dirpath, dirnames, filenames in os.walk(SRC):
        if "paper_trader.py" in filenames:
            full = os.path.join(dirpath, "paper_trader.py")
            rel  = os.path.relpath(full, SRC)
            mod  = rel[:-3].replace(os.sep, ".")  # strip .py, swap slashes -> dots
            if not mod.startswith("hybrid_ai_trading"):
                mod = "hybrid_ai_trading." + mod
            return mod
    raise RuntimeError("Could not find paper_trader.py anywhere under src/")

log("HAT direct paper daemon starting...")

try:
    module_name = _discover_paper_trader_module()
    log(f"Discovered paper_trader module: {module_name}")
    module = importlib.import_module(module_name)
    run_paper_session = getattr(module, "run_paper_session")

    # --- Build a call wrapper that respects the signature (with args) ---
    sig = inspect.signature(run_paper_session)
    params = list(sig.parameters.values())

    def _ensure_log_path(args: argparse.Namespace) -> argparse.Namespace:
        """
        Ensure args.log_path exists and points to a .logs file under ROOT.
        """
        log_dir = os.path.join(ROOT, ".logs")
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            log(f"Warning: failed to create log dir {log_dir!r}: {e!r}")

        if not hasattr(args, "log_path") or getattr(args, "log_path", None) in (None, ""):
            log_file = os.path.join(log_dir, "paper_direct.jsonl")
            setattr(args, "log_path", log_file)
            log(f"Using default args.log_path={log_file!r}")
        return args

    def _build_args():
        """
        Try to construct the args object expected by run_paper_session(args):
        - Look for a parser builder on the module (build_parser/make_parser/create_parser/get_parser).
        - If found, use parser.parse_args([]) for defaults.
        - Otherwise, return a Namespace with at least log_path set.
        """
        parser = None
        for name in ("build_parser", "make_parser", "create_parser", "get_parser"):
            fn = getattr(module, name, None)
            if callable(fn):
                try:
                    parser = fn()
                    log(f"Using parser from module.{name}()")
                    break
                except Exception as e:
                    log(f"Error calling module.{name}(): {e!r}")

        if parser is not None:
            try:
                # No CLI args -> defaults only
                args = parser.parse_args([])
                return _ensure_log_path(args)
            except Exception as e:
                log(f"Error in parser.parse_args([]): {e!r}")

        log("No parser factory found; using empty argparse.Namespace() for args.")
        args = argparse.Namespace()
        return _ensure_log_path(args)

    if len(params) == 0:
        # Legacy style: run_paper_session() with no args
        def call_run_paper_session():
            run_paper_session()
    else:
        # Modern style: run_paper_session(args)
        def call_run_paper_session():
            args = _build_args()
            log(f"Calling run_paper_session(args={args!r})")
            run_paper_session(args)

except Exception as e:
    log(f"IMPORT/DISCOVERY ERROR in hat_paper_direct: {e!r}")
    traceback.print_exc()
    raise

def main() -> None:
    """
    Daemon-style paper session runner:
    - repeatedly calls run_paper_session(...)
    - logs start/end
    - on error, logs traceback and retries after a delay
    """
    log("Entering paper session loop...")
    while True:
        log("Calling run_paper_session() wrapper...")
        try:
            call_run_paper_session()
            log("run_paper_session() wrapper returned cleanly.")
        except Exception as e:
            log(f"ERROR in run_paper_session() wrapper: {e!r}")
            traceback.print_exc()
        log("Sleeping 60 seconds before next run_paper_session() cycle...")
        time.sleep(60)

if __name__ == "__main__":
    main()