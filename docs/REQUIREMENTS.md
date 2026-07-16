# Requirements

## Functional Requirements

- Ingest ordered image sequences from a local folder.
- Preserve original files and write corrected outputs separately.
- Parse common metadata where available, starting with timestamp and camera/image dimensions.
- Support a reference frame selection strategy, initially first frame or explicit frame.
- Estimate rotation angles from one or more evidence sources.
- Apply rotation compensation with configurable interpolation and output format.
- Produce a machine-readable and human-readable report of angle estimates, sources, assumptions, and warnings.

## Rotation Evidence Requirements

The estimator layer should allow multiple providers:

- `geometry`: observer location, capture time, and target coordinates.
- `metadata`: frame metadata, capture software fields, FITS/XISF headers, EXIF where relevant.
- `image_registration`: star or feature matching against a reference frame.
- `mount_telemetry`: ASCOM/INDI or exported mount data.
- `orientation_sensor`: scope-mounted inclinometer, compass, IMU, tube/mount attitude, or rotator-like telemetry.

Evidence providers should report uncertainty and failure reasons. The reconciler should be able to choose, combine, or reject evidence instead of silently averaging nonsense.

The initial angle evidence report schema is `astro-rotator.angle-evidence-report.v1`; see `docs/ANGLE_EVIDENCE_REPORT_SCHEMA.md`.

The first supported image-format and metadata contract is defined in `docs/IMAGE_FORMATS_AND_METADATA.md`: dependency-free PGM fixtures, FITS for astronomy-native frame catalogs, and TIFF for interchange/output.

Scope-mounted inclinometer evidence uses the calibration and confidence model in `docs/INCLINOMETER_CALIBRATION_CONFIDENCE.md`. Inclinometer readings are calibrated into tube altitude with explicit uncertainty terms; they constrain or validate geometry rather than directly replacing parallactic-angle or image-registration evidence.

## Geometry Notes

The expected starting formula is based on parallactic angle change. A common form is:

```text
q = atan2(sin(H), tan(phi) * cos(delta) - sin(delta) * cos(H))
```

Where `H` is hour angle, `phi` is observer latitude, and `delta` is target declination. The compensation angle is the change in field orientation relative to the reference frame. Sign convention, axis orientation, and camera parity must be calibrated against image-derived results before being trusted.

The first geometry spike uses hour angle, latitude, and declination directly. The CLI can also derive hour angle from per-frame UTC capture timestamps, observer longitude, and target right ascension using a compact GMST/local sidereal time conversion. Its provisional image-space sign convention matches the synthetic fixtures: positive frame rotation is counterclockwise in displayed image coordinates, and derotation compensation is the negative of that image rotation. Camera parity and optical inversion remain explicit calibration work.

The first CLI geometry path supports both direct geometry flags, using per-frame hour angles, observer latitude, and target declination, and timestamp/location/target flags, using per-frame UTC timestamps, observer latitude/longitude, target right ascension, and target declination. Longitude is positive eastward. The timestamp path intentionally omits nutation, polar motion, refraction, and higher-precision astrometry corrections; those remain later backend/calibration work.

## Image Registration Notes

The first image-registration spike works on deterministic synthetic PGM fixtures with a dependency-free star detector and pairwise transform fitter. It estimates rotation and translation from star-like local maxima, using the same positive counterclockwise displayed-image convention as the synthetic fixture manifest. This is a correctness/sign-convention spike, not the final backend; scikit-image, OpenCV, SEP, or photutils can replace the implementation once the evidence/report shape is stable.

The first derotation engine supports dependency-free 8-bit PGM outputs only. It uses the image-registration estimator to derive a compensation angle relative to the selected reference frame, writes corrected frames separately, and records interpolation, canvas, fill, and transform diagnostics in the evidence report. FITS/TIFF derotation output is a later backend item; current FITS/TIFF support remains metadata-catalog oriented.

## Orientation Sensor Notes

The first inclinometer model treats a scope-mounted digital inclinometer as calibrated tube-altitude evidence. It records mounting offset, polarity, scale, calibration method, independent uncertainty terms, and a confidence score derived from total angular uncertainty. Inclinometer-only evidence should not claim a derotation angle until it is fused with geometry or another attitude model.

## Non-Functional Requirements

- Deterministic tests for angle math.
- Deterministic synthetic star-field fixtures with manifests recording known rotation, translation, pivot, seed, and coordinate convention.
- Reproducible outputs for the same inputs and settings.
- Clear handling of missing metadata.
- No network dependency for normal derotation.
- Local-first processing.
- Reasonable performance on typical hobbyist stacks.
- Cross-platform design where practical.

## Data / Privacy Requirements

- Treat location, timestamps, and raw frames as potentially private.
- Do not upload images or metadata unless a future feature explicitly asks and the user approves.
- Make reports safe to share only after users understand what metadata they contain.

## Packaging Requirements

- Use the Python-first implementation stack documented in `docs/IMPLEMENTATION_STACK.md`.
- Prefer a library core plus CLI wrapper so integrations can call the math and derotation pipeline.
- Choose an open source license before accepting contributions.
