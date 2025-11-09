#!/usr/bin/env bash
set -euo pipefail
if command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoLogo -NoProfile -File "$@"
elif command -v powershell >/dev/null 2>&1; then
  exec powershell -NoLogo -NoProfile -File "$@"
else
  echo "Neither pwsh nor powershell found on PATH" >&2
  exit 127
fi
