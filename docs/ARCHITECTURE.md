# Architecture

## Shape

Astro Rotator should start as a small library core with a CLI wrapper.

```text
input frames
  -> metadata reader
  -> evidence providers
  -> angle reconciler
  -> derotation engine
  -> corrected frames + report
```

## Proposed Components

- `frame_catalog`: discovers frames, normalizes ordering, and captures metadata.
- `evidence`: pluggable providers for geometry, metadata, mount telemetry, sensors, and image registration.
- `angle_model`: units, coordinate transforms, sign conventions, and uncertainty representation.
- `reconciler`: selects or combines angle estimates and records why.
- `rotator`: applies the image transform, interpolation, canvas/crop policy, masks, and output format.
- `reporting`: writes JSON plus readable summaries for debugging and repeatability.
- `cli`: thin command-line interface over the core.
- `testdata`: deterministic synthetic star-field fixtures with known rotation truth for sign-convention, registration, and derotation tests.

## Key Design Decisions To Make

- First image formats: FITS, XISF, TIFF, DSLR RAW, PNG/JPEG for tests, or a layered approach.
- Report schema.
- Default interpolation and crop policy.
- Test-data strategy and licensing. Synthetic fixture requirements are defined in `docs/SYNTHETIC_STAR_FIELD_GENERATOR.md`; external real stacks remain development data unless redistribution rights are explicit.

The first report schema is defined in `docs/ANGLE_EVIDENCE_REPORT_SCHEMA.md` and implemented in `astro_rotator.reporting`.
The first image-format and normalized metadata contract is defined in `docs/IMAGE_FORMATS_AND_METADATA.md` and implemented as data models in `astro_rotator.frame_catalog`.
The first scope-mounted inclinometer calibration and confidence model is defined in `docs/INCLINOMETER_CALIBRATION_CONFIDENCE.md` and implemented as helpers in `astro_rotator.evidence.inclinometer`.
Open-source tool and workflow research is recorded in `docs/OPEN_SOURCE_TOOLS_AND_WORKFLOWS.md`; it sets the boundary between reusable evidence backends, workflow compatibility, and out-of-scope stacker/capture-control features.
The first derotation engine is a dependency-light PGM implementation in `astro_rotator.rotator`, using same-size canvas output, nearest or bilinear interpolation, and image-registration evidence from the current PGM estimator.

## Implementation Stack

The MVP is Python-first. See `docs/IMPLEMENTATION_STACK.md` for the language, dependency, packaging, and format-support decisions.

## Risk Areas

- Sign conventions across sky coordinates, image axes, mirrored optics, and camera orientation.
- Sparse/noisy fields where image registration has too little signal.
- Metadata that is present but wrong.
- Low-cost compass, inclinometer, and IMU data distorted by metal, motors, vibration, flexure, and local magnetic weirdness.
- Users expecting impossible recovery from badly trailed or undersampled frames.
