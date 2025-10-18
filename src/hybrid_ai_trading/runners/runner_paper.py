# --- HAT heartbeat (runner) ---
try:
    import os, sys
except Exception:
    pass
print("HAT runner started argv=%s host=%s port=%s" % (" ".join(sys.argv), os.getenv("IB_HOST"), os.getenv("IB_PORT")))
# --- end HAT heartbeat (runner) ---

import os, sys, subprocess, pathlib
def main():
    os.environ.setdefault("PYTHONPATH", f"{pathlib.Path.cwd()/'src'};{os.environ.get('PYTHONPATH','')}")
    cmd = [sys.executable, "src/hybrid_ai_trading/runners/paper_trader.py", *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd))
if __name__ == "__main__":    main()