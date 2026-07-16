# Goal

Create a software-based image rotator for astrophotography captured on altazimuth mounts.

## Success Criteria

- Given a stack of timestamped frames, the tool can select a reference frame and estimate relative rotation angles.
- At least one geometry-based estimator is implemented using observer location, target coordinates, and capture time.
- At least one image-based estimator is implemented using star/feature matching between frames.
- The tool can derotate frames and write outputs without losing the original data.
- The tool produces an angle/evidence report that can be inspected and tested.
- The math and sign conventions are covered by deterministic tests.

## Initial MVP

A CLI command roughly shaped like:

```text
astro-rotator derotate --input frames/ --output derotated/ --reference first --angle-source geometry --geometry-timestamps ... --geometry-latitude ... --geometry-longitude ... --geometry-right-ascension ... --geometry-declination ...
```

The exact interface should wait until requirements and sample data are clearer.

## Later Possibilities

- Live-stack helper mode.
- Siril, PixInsight, KStars/Ekos, N.I.N.A., ASIAIR, or SharpCap integration research.
- GPU acceleration.
- Calibration workflow for compass, scope-mounted inclinometer, IMU, and mount telemetry.
- Visual diagnostics for rotation residuals.
