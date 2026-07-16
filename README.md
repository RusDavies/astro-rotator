# astro-rotator

## Purpose

Astro Rotator is an open source software project for compensating field rotation in astrophotography captured on altazimuth mounts.

Altazimuth mounts are mechanically simple and common, but long imaging sessions rotate the sky relative to the camera sensor. That makes stacking harder unless the images are derotated accurately. Mechanical field rotators exist, but they can be expensive, complex, and still need careful calibration. This project explores a software-first path: estimate the required compensation angle from available evidence, then rotate frames before or during stacking.

## First Useful Outcome

Build a command-line prototype that can:

- Read a sequence of astrophotography frames and metadata.
- Estimate each frame's rotation relative to a chosen reference frame.
- Apply derotation using a reproducible interpolation method.
- Emit corrected frames plus an evidence report showing the angle source, uncertainty, and any assumptions.

## Angle Evidence Sources

Initial candidate inputs:

- Clock and accurate capture timestamps.
- GPS or configured observer latitude, longitude, and elevation.
- Target coordinates, either entered by the user or derived from plate solving.
- Prior photos in the stack, including EXIF/FITS/XISF metadata.
- Scope-mounted compass, mount azimuth, or mount telemetry.
- Scope-mounted inclinometer for tube altitude/elevation evidence.
- Altitude/azimuth encoders from the mount.
- Camera or scope orientation from IMU/inclinometer data where available.
- Plate solving against star catalogs.
- Star matching, optical flow, or feature tracking between frames.
- ASCOM/INDI driver telemetry.
- NTP/GPS-disciplined clock quality indicators.

## Starting Assumption

The most reliable MVP path is probably hybrid:

1. Use astronomical geometry when location, time, and target coordinates are known.
2. Use image registration between frames as the empirical correction and sign check.
3. Record uncertainty instead of pretending every input source is equally trustworthy. Which, naturally, would be how a computer gets blamed for a mount doing interpretive dance.

## Project Status

This is an early prototype. The current implementation focuses on deterministic
geometry, image-registration, reporting, and PGM derotation paths so the math
and sign conventions can be tested before broader format and workflow support
is added.

See `ROADMAP.md` for the current public-facing development direction.

## License

MIT. See `LICENSE`.
