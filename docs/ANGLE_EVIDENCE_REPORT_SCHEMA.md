# Angle Evidence Report Schema

Schema identifier: `astro-rotator.angle-evidence-report.v1`

The angle evidence report records the selected frame rotation, derotation compensation, and all supporting or rejected evidence for each frame. It is meant to be machine-readable first and human-inspectable second.

## Coordinate Convention

The report must state the image-space convention used by every frame angle:

- origin: normally `top_left`;
- x axis: normally `right`;
- y axis: normally `down`;
- positive rotation: currently `counterclockwise_image_space`;
- angle unit: degrees.

This convention must match synthetic fixture manifests until a later camera-parity/optics calibration layer says otherwise.

## Top-Level Shape

```json
{
  "schema": "astro-rotator.angle-evidence-report.v1",
  "generated_by": "astro-rotator",
  "reference_frame_path": "frame_000.pgm",
  "coordinate_convention": {
    "origin": "top_left",
    "x_positive": "right",
    "y_positive": "down",
    "positive_rotation": "counterclockwise_image_space"
  },
  "assumptions": ["synthetic_fixture"],
  "warnings": [],
  "frames": []
}
```

## Frame Entries

Each frame entry records the selected angle and all available evidence:

```json
{
  "frame_path": "frame_001.pgm",
  "selected_rotation_degrees": 1.45,
  "selected_derotation_degrees": -1.45,
  "selected_source": "image_registration",
  "warnings": [],
  "evidence": []
}
```

`selected_rotation_degrees` is the estimated target-frame rotation relative to the report reference frame. `selected_derotation_degrees` is the compensation to apply when rotating the target frame back toward the reference convention.

## Evidence Entries

Evidence sources currently use these source names:

- `geometry`
- `image_registration`
- `metadata`
- `mount_telemetry`
- `orientation_sensor`

Statuses:

- `ok`
- `warning`
- `failed`
- `not_available`

Example:

```json
{
  "source": "image_registration",
  "status": "ok",
  "frame_path": "frame_001.pgm",
  "reference_frame_path": "frame_000.pgm",
  "rotation_degrees": 1.45,
  "derotation_degrees": -1.45,
  "uncertainty_degrees": 0.1,
  "confidence": 0.9,
  "method": "synthetic_pairwise_star_fit.v1",
  "evidence_role": "selected",
  "transform_diagnostics": {
    "transform_model": "similarity_2d",
    "inlier_count": 28,
    "rejected_match_count": 3,
    "rms_error_pixels": 0.42,
    "residual_summary": {
      "median_pixels": 0.31,
      "p95_pixels": 0.72
    },
    "preprocessing": {
      "source": "synthetic_pgm",
      "stretch": "none"
    },
    "parameters": {
      "rotation_degrees": 1.45,
      "translation_pixels": [0.2, -0.1]
    }
  },
  "assumptions": [],
  "warnings": [],
  "diagnostics": {
    "matched_stars": 28,
    "rms_error_pixels": 0.42
  }
}
```

Failed or unavailable evidence may omit angle fields, but `ok` evidence must include `rotation_degrees`. Providers should explain missing or questionable evidence through `status`, `warnings`, `assumptions`, and `diagnostics` rather than silently disappearing.

`evidence_role` is optional and records how the reconciler treated the evidence:

- `selected`: used for the frame's selected angle;
- `fallback`: valid but not used unless the preferred source fails;
- `advisory`: useful context but not eligible for direct selection;
- `rejected`: evaluated and deliberately rejected.

`transform_diagnostics` is optional but should be present for image-registration, WCS reprojection, optical-flow, or backend-specific transform evidence. It records:

- `transform_model`: model family such as `rotation_only`, `similarity_2d`, `affine_2d`, `homography_2d`, `wcs_reprojection`, or a backend-specific name;
- `inlier_count`: accepted matches or constraints used by the fit;
- `rejected_match_count`: rejected candidate matches, outliers, or constraints;
- `rms_error_pixels`: root-mean-square residual in pixels when applicable;
- `residual_summary`: named residual statistics, normally pixel units;
- `preprocessing`: input state that affects the fit, such as stretch, calibration, downsample scale, star detector, threshold, or mask policy;
- `parameters`: transform parameters needed for debugging or reproducibility, such as angle, translation, scale, pivot, matrix coefficients, or WCS operation name.

Frame-level `selected_source` still records the chosen source category. Evidence-level `evidence_role` lets multiple entries from the same source category explain whether they were selected, fallback, advisory, or rejected.

The current dependency-free PGM image-registration estimator populates this shape through `ImageRegistrationEstimate.to_angle_evidence()`. Its transform model is `similarity_2d`; its preprocessing block records the PGM input format, local-maxima centroid detector, star cap, match tolerance, and detected-star counts; and its parameters include rotation plus pivot-adjusted and affine translation values.

## Intent Check

This schema keeps the project aligned with the current product intent: it explains where an angle came from, how confident the tool is, what assumptions were made, and what compensation should be applied. It does not turn the project into a full stacker, mount controller, or generic media pipeline.
