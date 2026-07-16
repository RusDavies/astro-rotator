# Product Brief

## Summary

Astro Rotator is an open source software image-derotation tool for astrophotography workflows using altazimuth telescope mounts.

## Problem

Altazimuth mounts track altitude and azimuth rather than rotating with the sky. During a capture sequence, the field rotates on the camera sensor. That rotation complicates image stacking, reduces usable exposure length, and can force users toward mechanical field rotators or equatorial mounts.

Mechanical rotators can help, but they add cost, complexity, backlash, calibration burden, and another failure point. Software derotation should be able to recover much of the value when the image sequence contains enough timing, geometry, metadata, or star-field evidence.

## Users / Stakeholders

- Amateur astrophotographers using altazimuth mounts.
- EAA users who want better live or near-live stacking.
- Developers integrating derotation into capture, preprocessing, or stacking pipelines.
- Maintainers and contributors who need reproducible math and test data.

## Goals

- Estimate field rotation compensation angle for each frame in a stack.
- Support multiple evidence sources: time/location/target geometry, metadata, mount telemetry, plate solving, and image-to-image registration.
- Derotate frames with documented interpolation, cropping, masking, and quality tradeoffs.
- Report confidence, assumptions, and input provenance for every computed angle.
- Provide a small CLI-first MVP before larger UI or plugin work.

## Non-Goals

- Build a complete image stacker in the first phase.
- Replace all mechanical rotators for every imaging case.
- Control mounts or cameras directly in the MVP.
- Promise perfect compensation without calibration or image evidence.

## Current Alternatives

- Mechanical field rotators.
- Equatorial mounts or wedge setups.
- Existing stacking tools with rotation-aware alignment.
- Manual preprocessing in astronomy/image-processing tools.
- Shorter exposures and accepting crop/loss artifacts.

## Differentiation Hypothesis

The useful niche is not "rotate pixels, somehow." Existing tools can rotate images. The value is in robustly deriving, reconciling, and explaining the compensation angle from mixed astronomy, metadata, mount, and image evidence.

## Assumptions

- Many useful input stacks include enough timestamp, location, target, or star-field evidence to estimate rotation without extra hardware.
- Image-derived rotation can calibrate or override geometry-derived estimates when metadata is incomplete or wrong.
- A transparent evidence report will be more useful than a black-box angle.

## Unknowns

- How accurate low-cost compass, scope-mounted inclinometer, and IMU inputs are near typical telescope hardware.
- How robust image registration is on sparse fields, nebulosity-heavy frames, clouds, satellite trails, and low SNR.
- Which interpolation/cropping choices are acceptable for common astrophotography workflows.
- Whether the project should target FITS/XISF first, common DSLR raw workflows first, or generic image formats first.

## Security / Privacy Notes

The project should avoid collecting telemetry by default. Local metadata may include location and timestamps, so docs should warn users before sharing raw frames or logs publicly.

## Open Source Notes

The repository is open source under the MIT License.
