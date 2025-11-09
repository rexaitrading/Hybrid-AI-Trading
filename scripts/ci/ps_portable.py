import os
import shutil
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: ps_portable.py <ps1-script> [args...]", file=sys.stderr)
        sys.exit(2)
    exe = shutil.which("pwsh") or shutil.which("powershell")
    if not exe:
        print("Neither pwsh nor powershell found on PATH", file=sys.stderr)
        sys.exit(127)
    script, args = sys.argv[1], sys.argv[2:]
    cmd = [exe, "-NoLogo", "-NoProfile", "-File", script] + args
    try:
        sys.exit(subprocess.call(cmd))
    except OSError as e:
        print(f"Failed to exec {cmd}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
