#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -m pip_audit --version >/dev/null 2>&1; then
  cat >&2 <<'EOF'
pip-audit is not installed.

Install it with:
  python -m pip install pip-audit==2.10.1
EOF
  exit 1
fi

"$PYTHON" -m pip_audit --progress-spinner off

echo "astro-rotator security checks passed"
