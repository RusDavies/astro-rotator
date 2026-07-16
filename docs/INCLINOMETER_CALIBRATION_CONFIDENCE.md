# Scope-Mounted Inclinometer Calibration And Confidence

This document defines how Astro Rotator should treat a scope-mounted inclinometer as angle evidence.

The important boundary: an inclinometer by itself is not a derotation estimator. It measures tube altitude or attitude after calibration. The derotation pipeline can use that calibrated attitude to validate geometry, detect bad metadata, constrain a future sensor-fusion estimator, or explain why orientation-sensor evidence was rejected.

## Measurement Model

Raw sensor readings are normalized to tube altitude in degrees:

```text
tube_altitude_degrees = polarity * scale * raw_tilt_degrees + offset_degrees
```

Fields:

- `raw_tilt_degrees`: reading from the inclinometer in its own orientation convention.
- `polarity`: `1` when raw tilt increases with tube altitude, `-1` when it decreases.
- `scale`: multiplier for sensors whose slope is not exactly one degree per degree.
- `offset_degrees`: zero/reference offset after mounting.
- `tube_altitude_degrees`: calibrated telescope tube altitude above the local horizon.

The first implementation lives in `astro_rotator.evidence.inclinometer` as `InclinometerCalibration`.

## Calibration Methods

Supported method names:

- `single_point_horizon`: one known reference, usually a leveled tube or true horizon reference. This solves offset only.
- `two_point_altitude`: two known altitude references. This can solve offset, polarity, and scale.
- `plate_solved_altitude`: derive known tube altitude from plate solving plus time/location geometry.
- `factory_or_manual`: user-supplied or device-supplied calibration without enough local validation.

Minimum useful calibration record:

```json
{
  "method": "single_point_horizon",
  "raw_tilt_degrees": 1.2,
  "known_altitude_degrees": 0.0,
  "polarity": 1,
  "scale": 1.0,
  "offset_degrees": -1.2
}
```

For a two-point calibration, store both raw/known pairs and the residual after fitting. For a plate-solved calibration, store the plate-solve source and the geometry assumptions used to derive the known altitude.

## Uncertainty Model

Total uncertainty is the root-sum-square of independent components:

```text
uncertainty_degrees = sqrt(sum(component_degrees^2))
```

Recommended component names:

- `sensor_repeatability`: jitter from repeated readings at fixed attitude.
- `calibration_residual`: residual error from the calibration fit.
- `mounting_flexure`: movement between the inclinometer and optical tube.
- `temperature_drift`: reading drift over a session.
- `vibration_or_settling`: tripod, mount, focuser, cable, or handling movement.
- `timestamp_alignment`: mismatch between image exposure time and sensor sample time.
- `horizon_or_reference_error`: error in the physical reference used for calibration.

`InclinometerCalibration` includes explicit `UncertaintyTerm` entries plus optional `residual_rms_degrees`.

## Confidence Model

Confidence is a bounded report score derived from total uncertainty:

```text
<= 0.25 deg -> 0.95
<= 0.50 deg -> 0.85
<= 1.00 deg -> 0.70
<= 2.00 deg -> 0.50
<= 5.00 deg -> 0.25
>  5.00 deg -> 0.05
```

Provider status should be:

- `ok`: uncertainty is at most `1.0` degree and no warnings are present.
- `warning`: uncertainty is above `1.0` degree, or warnings are present.
- `failed`: uncertainty is above `5.0` degrees, or the calibration is unusable.

These thresholds are intentionally conservative. Cheap digital inclinometers can look precise while being wrong because the mounting surface moved, the tube flexed, or the calibration reference was nonsense with a confident face.

## Report Mapping

Orientation-sensor evidence should use:

- `source`: `orientation_sensor`
- `method`: `scope_inclinometer.v1`
- `confidence`: derived from the uncertainty model.
- `uncertainty_degrees`: total uncertainty from the component model.
- `diagnostics.sensor`: `scope_mounted_inclinometer`
- `diagnostics.raw_tilt_degrees`
- `diagnostics.calibrated_tube_altitude_degrees`
- `diagnostics.calibration_method`
- `diagnostics.uncertainty_terms`

Until the reconciler can fuse attitude with geometry, inclinometer-only evidence should not claim `rotation_degrees`. It should be reported as `warning` or `not_available` if it only constrains altitude. Once fused with geometry, the resulting provider can emit a normal rotation estimate and preserve the inclinometer details in diagnostics.

## Acceptance Criteria

- The raw-to-calibrated-altitude transform is explicit and testable.
- Uncertainty terms are named and preserved in report diagnostics.
- Confidence is derived from uncertainty, not hand-waved per provider.
- The docs state that inclinometer evidence constrains attitude and does not directly replace image registration or parallactic geometry.
- Future sensor fusion can reuse the same diagnostics without changing the report schema.
