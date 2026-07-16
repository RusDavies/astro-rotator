# Image Formats and Metadata

This document defines the first supported image formats and normalized metadata fields for the MVP. It is a format/metadata contract, not a full parser implementation.

## First Supported Formats

### PGM

Purpose:

- deterministic synthetic fixtures;
- dependency-free registration and sign-convention tests;
- tiny generated files that do not need to be committed.

Implemented support level:

- read 8-bit binary PGM/P5 fixtures;
- no capture metadata in the image file itself;
- use the synthetic `manifest.json` as the source of truth for generated rotation, translation, pivot, seed, and coordinate convention.

### FITS

Purpose:

- astronomy-native input and future output;
- metadata-rich workflows where capture time, exposure, instrument, target, and site fields may already exist.

Implemented support level:

- first astronomy-native format for real frame-catalog work;
- dependency-free primary-header parser for the initial fields below;
- use `astropy` later when full FITS compatibility is needed;
- preserve original headers in `raw_fields` where practical;
- normalize common fields into the frame metadata model.

Initial FITS fields to recognize, where present:

- geometry: `NAXIS`, `NAXIS1`, `NAXIS2`, `BITPIX`;
- capture time: `DATE-OBS`, `DATE-BEG`, `DATE-END`;
- exposure: `EXPTIME`, `EXPOSURE`;
- instrument: `INSTRUME`, `CAMERA`, `TELESCOP`, `FILTER`;
- detector settings: `GAIN`, `OFFSET`, `CCD-TEMP`, `SET-TEMP`, `XBINNING`, `YBINNING`;
- target: `OBJECT`, `OBJCTRA`, `OBJCTDEC`, `RA`, `DEC`;
- observer/site: `SITELAT`, `SITELONG`, `OBSGEO-L`, `OBSGEO-B`, `OBSGEO-H`;
- mount/pointing when present: `ALT`, `AZ`, `OBJCTALT`, `OBJCTAZ`.

### TIFF

Purpose:

- interchange format for deterministic intermediate/output frames;
- useful for high-bit-depth image processing when FITS is not desired.

Implemented support level:

- dimensions, bit depth, channel count, and basic timestamp when available;
- dependency-free classic-TIFF IFD reader for the initial geometry/date fields;
- use `tifffile` later when full TIFF compatibility is needed;
- prefer sidecar metadata for astronomy fields that TIFF does not reliably standardize.

## Later Formats

Do not block the MVP on these:

- DSLR RAW formats such as CR2/NEF/ARW via `rawpy`;
- XISF for PixInsight workflows;
- PNG/JPEG as user-facing inputs;
- SER/video containers and live-stream sources;
- GStreamer buffers for live adapter work.

## Normalized Metadata Model

The normalized model is implemented in `astro_rotator.frame_catalog`.

### Frame Identity

- `path`
- `format`: `pgm`, `fits`, or `tiff`
- `frame_index`

### Geometry

- `width`
- `height`
- `bit_depth`
- `channel_count`
- `bayer_pattern`

### Capture

- `captured_at_utc`
- `exposure_seconds`
- `camera_name`
- `telescope_name`
- `filter_name`
- `gain`
- `offset`
- `sensor_temperature_celsius`
- `focal_length_mm`
- `f_number`
- `iso`

### Astrometry / Site / Pointing

- `target_name`
- `right_ascension_degrees`
- `declination_degrees`
- `observer_latitude_degrees`
- `observer_longitude_degrees`
- `observer_elevation_meters`
- `mount_altitude_degrees`
- `mount_azimuth_degrees`

### Provenance

- `raw_fields`: original format-specific metadata fields that fed normalization;
- `warnings`: missing, conflicting, suspicious, or unsupported metadata notes.

## Privacy

Location, timestamps, target history, and equipment metadata can be private. Reports and sidecars should preserve useful provenance, but user-facing docs must warn before sharing raw frames, normalized metadata, or generated reports publicly.

## Parser Work

The first parser implementation lives in `astro_rotator.frame_catalog` and returns `FrameMetadata` objects. It is intentionally narrow and dependency-free. RAW and XISF remain explicit follow-up work.
