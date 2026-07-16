# Contributing

Astro Rotator is an early prototype. Contributions are welcome once they keep
the project focused on software field derotation for altazimuth astrophotography
and preserve the testable math/reporting boundaries.

## Development Setup

Use Python 3.12 or newer.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
scripts/check.sh
```

## Contribution Guidelines

- Keep changes scoped to field-rotation estimation, evidence reporting, image
  derotation, supported image metadata, or closely related CLI/library support.
- Add or update deterministic tests for math, image transforms, parsers, report
  schema changes, and CLI behavior.
- Do not commit raw astrophotography frames, downloaded sample archives, private
  location/timestamp metadata, generated reports from personal data, or large
  binary assets unless redistribution rights and size handling are explicit.
- Record user-facing assumptions in docs or report diagnostics rather than
  hiding them in implementation details.
- Preserve local-first processing. Network access should not be required for
  normal derotation.

## Before Opening a Pull Request

Run:

```bash
scripts/check.sh
scripts/security_check.sh
```

If `pip-audit` is not installed locally, `scripts/security_check.sh` will explain
how to install it.
