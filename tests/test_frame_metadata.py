from __future__ import annotations

import pytest

from astro_rotator.frame_catalog import (
    AstrometryMetadata,
    CaptureMetadata,
    FrameGeometry,
    FrameMetadata,
)


def test_frame_metadata_serializes_without_missing_optional_values() -> None:
    metadata = FrameMetadata(
        path="frame_001.fits",
        format="fits",
        frame_index=1,
        geometry=FrameGeometry(width=1024, height=768, bit_depth=16),
        capture=CaptureMetadata(
            captured_at_utc="2026-07-14T04:00:00Z",
            exposure_seconds=15.0,
            camera_name="ExampleCam",
        ),
        astrometry=AstrometryMetadata(
            target_name="M31",
            right_ascension_degrees=10.6847083,
            declination_degrees=41.26875,
        ),
        raw_fields={"DATE-OBS": "2026-07-14T04:00:00Z"},
    )

    payload = metadata.to_dict()

    assert payload["format"] == "fits"
    assert payload["geometry"]["width"] == 1024
    assert payload["capture"]["exposure_seconds"] == 15.0
    assert payload["capture"]["camera_name"] == "ExampleCam"
    assert "iso" not in payload["capture"]
    assert payload["astrometry"]["target_name"] == "M31"
    assert payload["raw_fields"]["DATE-OBS"] == "2026-07-14T04:00:00Z"


def test_frame_geometry_requires_positive_dimensions() -> None:
    with pytest.raises(ValueError, match="width and height"):
        FrameGeometry(width=0, height=768, bit_depth=16)


def test_capture_metadata_validates_obvious_bad_values() -> None:
    with pytest.raises(ValueError, match="exposure_seconds"):
        CaptureMetadata(exposure_seconds=-1.0)
    with pytest.raises(ValueError, match="iso"):
        CaptureMetadata(iso=0)
