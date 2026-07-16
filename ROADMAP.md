# Roadmap

Astro Rotator is currently a prototype focused on proving the derotation math,
evidence model, and CLI workflow before expanding into broader astrophotography
formats and integrations.

## Current Focus

- Keep the core angle-estimation and derotation pipeline deterministic and well tested.
- Validate geometry-derived rotation against image-registration evidence.
- Preserve clear report output for assumptions, diagnostics, and selected evidence.
- Keep real sample data out of the repository unless redistribution rights are explicit.

## Near-Term Work

- Add sexagesimal RA/Dec parsing and friendlier site/target input helpers.
- Add FITS/TIFF derotation output backends after the PGM path remains stable.
- Spike `astroalign` as an optional real-image registration backend.
- Define an ASCOM/Alpaca telemetry import contract before any live device access.

## Later Work

- Spike WCS-preserving derotation with Astropy `reproject` after FITS/WCS ingestion exists.
- Explore optional live/streaming adapters after the core transform model is stable.
- Add contribution, security, and dependency-audit workflows before treating the project as broadly contribution-ready.
