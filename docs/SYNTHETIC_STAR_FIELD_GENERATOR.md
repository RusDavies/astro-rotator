# Synthetic Star-Field Generator

The project needs deterministic image fixtures with known rotation truth before any geometry or image-registration result can be trusted. Real stacks are useful smoke tests, but they rarely include complete ground truth for location, target, optical parity, camera orientation, and actual sky motion.

## Purpose

The generator should create small, reproducible star-field stacks that exercise:

- rotation sign convention;
- image-axis orientation;
- translation plus rotation;
- crop/padding behavior;
- interpolation artifacts;
- missing or noisy stars;
- metadata/reporting of known truth.

These fixtures are not a full sky simulator. They are controlled test images for derotation math and registration plumbing.

## Initial Fixture Set

Start with three fixture families:

1. `pure_rotation`: reference image plus frames rotated around the image center by known angles.
2. `rotation_translation`: known rotation plus small x/y offsets to match real tripod or mount drift.
3. `noisy_sparse_field`: lower star count, brightness variation, background noise, and a few missing stars.

Each family should generate a short stack with the same manifest shape so the estimator tests can run against all of them.

## Coordinate and Sign Convention

Use image coordinates explicitly:

- origin: top-left pixel corner;
- x axis: positive right;
- y axis: positive down;
- angle unit: degrees in the manifest;
- positive image rotation: counterclockwise in mathematical image-space convention around the chosen pivot, before accounting for any future sky/camera parity model.

Every fixture must record the exact transform from the reference frame to each generated frame. The first tests should assert this convention directly, then later geometry tests can map parallactic-angle changes onto it.

## Generator Inputs

The implementation should support these deterministic inputs:

- `seed`: integer random seed.
- `width`, `height`: output dimensions.
- `star_count`: number of base stars.
- `background_level`: base background intensity.
- `noise_sigma`: Gaussian noise level.
- `psf_sigma`: star point-spread width in pixels.
- `angle_degrees`: list of per-frame rotations relative to the reference.
- `translation_pixels`: optional list of `[dx, dy]` translations relative to the reference.
- `missing_star_fraction`: optional per-frame probability of omitting a star.
- `hot_pixel_count`: optional count of non-star bright pixels.
- `output_format`: initially dependency-free PGM for exact generated fixtures. PNG, TIFF, and FITS can be added once format support is chosen.

Keep the first implementation small enough that generated fixtures can run in unit tests without large binary files in git.

## Manifest

Each generated stack should include a machine-readable manifest. A minimal shape:

```json
{
  "schema": "astro-rotator.synthetic-stack.v1",
  "name": "pure_rotation_seed_42",
  "generator": {
    "seed": 42,
    "width": 512,
    "height": 512,
    "star_count": 300,
    "background_level": 12.0,
    "noise_sigma": 1.5,
    "psf_sigma": 1.2
  },
  "coordinate_convention": {
    "origin": "top_left",
    "x_positive": "right",
    "y_positive": "down",
    "angle_unit": "degrees",
    "positive_rotation": "counterclockwise_image_space"
  },
  "reference_frame": "frame_000.png",
  "frames": [
    {
      "path": "frame_000.pgm",
      "angle_degrees_from_reference": 0.0,
      "translation_pixels_from_reference": [0.0, 0.0],
      "pivot_pixels": [256.0, 256.0]
    },
    {
      "path": "frame_001.pgm",
      "angle_degrees_from_reference": 0.5,
      "translation_pixels_from_reference": [1.0, -0.5],
      "pivot_pixels": [256.0, 256.0]
    }
  ]
}
```

The manifest is the source of truth for fixture tests. Estimators should never infer expected angles from file names.

## Test Expectations

Initial tests should verify:

- the generator is deterministic for the same seed and options;
- generated frames and manifests are reproducible byte-for-byte or within a documented tolerance;
- image-registration estimates recover known rotation within a fixture-specific tolerance;
- derotation reduces residual error relative to the reference frame;
- sign convention failures produce obvious failing tests.

The first useful tolerance can be generous. The point is to catch wrong sign, wrong pivot, wrong axis, and unit mistakes before chasing sub-pixel accuracy.

## Storage Policy

Prefer generating fixtures during tests instead of committing generated stacks. If small golden files become useful, keep them tiny, document the generator version and manifest, and avoid committing large real-world data. PGM is intentionally allowed for the first generated fixtures because it is simple, exact, and dependency-free; delivery formats can come later without changing the manifest truth model.

External raw stacks stay outside git unless their license and size handling are explicitly resolved.
