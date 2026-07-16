# Implementation Stack

## Decision

Use Python for the MVP library and CLI.

Target Python 3.12+ for new development unless packaging constraints force a broader support window later. Python is the best first fit because the project needs astronomy coordinate math, FITS support, numerical arrays, image transforms, and fast iteration on test fixtures before performance bottlenecks are real.

## Core Runtime Dependencies

Start with a small dependency set:

- `numpy`: array representation, generated fixtures, angle math, and report-friendly numeric handling.
- `scipy`: interpolation, transforms, optimization helpers, and numerically tested utilities.
- `astropy`: time, coordinates, units, and FITS I/O.
- `scikit-image`: image registration, geometric transforms, feature detection, and simple image metrics.
- `tifffile`: TIFF read/write for deterministic fixtures and intermediate outputs.
- `pydantic`: validation and typed serialization for manifests and future evidence reports.
- `typer`: CLI entrypoints with readable help and low ceremony.

Keep OpenCV out of the default dependency set for the MVP. It is useful, but it is large, brings packaging friction, and overlaps with `scikit-image` for the first registration spikes. Add an optional OpenCV backend later only if measurements show it earns its keep.

## Development Dependencies

Use:

- `pytest` for tests.
- `ruff` for formatting/linting.
- `mypy` or `pyright` later if type coverage becomes valuable enough to enforce.

The first real test suite should cover the synthetic generator, manifest validation, sign convention, and a simple rotation-registration path.

## Optional / Later Dependencies

Add these only behind extras or later feature decisions:

- `rawpy`: DSLR RAW support through LibRaw. Useful for CR2/NEF/ARW development, but not part of the smallest install.
- `opencv-python-headless`: optional faster or alternate registration backend.
- `astroalign`: optional astronomy-specific WCS-free registration backend, to be evaluated after the evidence-provider interface is stable.
- `reproject`: optional WCS-preserving reprojection/resampling backend, to be evaluated after FITS/WCS or plate-solving ingestion exists.
- `sep` or `photutils`: astronomy-focused source extraction if generic feature detection struggles on sparse fields.
- `xisf`: XISF support if PixInsight workflows become an early target.
- GPU or native acceleration libraries only after profiling proves Python/scientific-stack performance is insufficient.

## Format Policy

Initial implementation should support:

- generated PGM fixtures for deterministic tests;
- FITS via `astropy` for astronomy-native workflows;
- TIFF as an interchange/output format.

Treat DSLR RAW and XISF as explicit follow-up work. The external CR2 stack can drive experiments, but RAW support should not block the first math and registration fixtures.

## Packaging Shape

Use a normal Python package with a library core plus CLI wrapper:

```text
src/astro_rotator/
  angle_model/
  evidence/
  frame_catalog/
  reporting/
  rotator/
  testdata/
  cli.py
tests/
```

The package should be runnable from source during development and installable with a standard `pyproject.toml`.

## Rationale

The early risk is not CPU speed. The early risk is wrong math, wrong sign convention, missing provenance, and image-registration behavior that looks plausible while being subtly wrong. Python's astronomy and image-processing ecosystem lets the project attack those risks quickly and visibly.

If a future derotation kernel needs native speed, isolate that behind the library API after the behavior is tested. First make it correct; then teach it to sprint.
