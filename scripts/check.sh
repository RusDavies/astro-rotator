#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

test -f README.md
test -f ROADMAP.md
test -f docs/PRODUCT_BRIEF.md
test -f docs/REQUIREMENTS.md
test -f docs/ARCHITECTURE.md
test -f docs/SAMPLE_DATA_CANDIDATES.md
test -f docs/IMPLEMENTATION_STACK.md
test -f docs/SYNTHETIC_STAR_FIELD_GENERATOR.md
test -f docs/ANGLE_EVIDENCE_REPORT_SCHEMA.md
test -f docs/IMAGE_FORMATS_AND_METADATA.md
test -f pyproject.toml
test -f src/astro_rotator/__init__.py
test -f tests/test_package.py

grep -q "altazimuth" README.md
grep -q "parallactic" docs/REQUIREMENTS.md
grep -q "image_registration" docs/REQUIREMENTS.md
grep -q "AstroCompress" docs/SAMPLE_DATA_CANDIDATES.md
grep -q "Python" docs/IMPLEMENTATION_STACK.md
grep -q "Synthetic Star-Field Generator" docs/SYNTHETIC_STAR_FIELD_GENERATOR.md
grep -q "angle-evidence-report" docs/ANGLE_EVIDENCE_REPORT_SCHEMA.md
grep -q "FITS" docs/IMAGE_FORMATS_AND_METADATA.md

"$PYTHON" -m compileall -q src tests
"$PYTHON" - <<'PY'
from __future__ import annotations

import pathlib
import tomllib

project = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
assert project["project"]["name"] == "astro-rotator"
assert project["project"]["requires-python"] == ">=3.12"
PY

if "$PYTHON" -m ruff --version >/dev/null 2>&1; then
  "$PYTHON" -m ruff check .
  "$PYTHON" -m ruff format --check .
fi

if "$PYTHON" -m pytest --version >/dev/null 2>&1; then
  PYTHONPATH=src "$PYTHON" -m pytest
else
  PYTHONPATH=src "$PYTHON" - <<'PY'
import astro_rotator

assert astro_rotator.__version__ == "0.1.0"
PY
fi

echo "astro-rotator checks passed"
