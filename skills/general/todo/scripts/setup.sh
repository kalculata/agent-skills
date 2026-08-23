#!/usr/bin/env bash
# Create the venv used to run todo.py. Safe to re-run.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv="$here/.venv"

if [ ! -x "$venv/bin/python" ]; then
  python3 -m venv "$venv"
  echo "created venv at $venv"
fi

"$venv/bin/pip" install -q -r "$here/requirements.txt"

"$venv/bin/pip" install -q --disable-pip-version-check -r "$here/requirements.txt"

"$venv/bin/python" - <<'PY'
import sqlite3, sys
assert sys.version_info >= (3, 8), f"python 3.8+ required, got {sys.version}"
print(f"ok: python {sys.version.split()[0]}, sqlite {sqlite3.sqlite_version}")
PY
