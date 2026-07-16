from __future__ import annotations

import struct

import pytest

from astro_rotator.frame_catalog import read_fits_metadata, read_frame_metadata, read_tiff_metadata
from astro_rotator.testdata import SyntheticStackConfig, generate_synthetic_stack


def test_read_pgm_metadata_from_synthetic_frame(tmp_path) -> None:
    generate_synthetic_stack(
        tmp_path,
        SyntheticStackConfig(width=17, height=13, star_count=5, angle_degrees=(0.0,)),
    )

    metadata = read_frame_metadata(tmp_path / "frame_000.pgm", frame_index=3)

    assert metadata.format == "pgm"
    assert metadata.frame_index == 3
    assert metadata.geometry.width == 17
    assert metadata.geometry.height == 13
    assert metadata.geometry.bit_depth == 8
    assert metadata.warnings == ("pgm_contains_no_capture_metadata",)


def test_read_fits_metadata_from_primary_header(tmp_path) -> None:
    path = tmp_path / "frame_001.fits"
    _write_minimal_fits(
        path,
        {
            "SIMPLE": True,
            "BITPIX": 16,
            "NAXIS": 2,
            "NAXIS1": 1024,
            "NAXIS2": 768,
            "DATE-OBS": "2026-07-14T04:00:00Z",
            "EXPTIME": 15.0,
            "INSTRUME": "ExampleCam",
            "TELESCOP": "ExampleScope",
            "FILTER": "L",
            "GAIN": 120,
            "CCD-TEMP": -10.5,
            "OBJECT": "M31",
            "OBJCTRA": "00:42:44.33",
            "OBJCTDEC": "+41:16:09.0",
            "SITELAT": 45.0,
            "SITELONG": -75.0,
            "OBSGEO-H": 100.0,
            "OBJCTALT": 55.0,
            "OBJCTAZ": 180.0,
        },
    )

    metadata = read_fits_metadata(path)

    assert metadata.format == "fits"
    assert metadata.geometry.width == 1024
    assert metadata.geometry.height == 768
    assert metadata.geometry.bit_depth == 16
    assert metadata.capture.captured_at_utc == "2026-07-14T04:00:00Z"
    assert metadata.capture.exposure_seconds == 15.0
    assert metadata.capture.camera_name == "ExampleCam"
    assert metadata.capture.telescope_name == "ExampleScope"
    assert metadata.capture.filter_name == "L"
    assert metadata.astrometry.target_name == "M31"
    assert metadata.astrometry.right_ascension_degrees == pytest.approx(10.6847083)
    assert metadata.astrometry.declination_degrees == pytest.approx(41.2691667)
    assert metadata.astrometry.observer_latitude_degrees == 45.0
    assert metadata.astrometry.observer_longitude_degrees == -75.0
    assert metadata.astrometry.mount_altitude_degrees == 55.0
    assert metadata.raw_fields["NAXIS1"] == 1024


def test_read_tiff_metadata_from_classic_tiff(tmp_path) -> None:
    path = tmp_path / "frame_001.tif"
    path.write_bytes(_minimal_tiff(width=640, height=480, bit_depth=16, samples=1))

    metadata = read_tiff_metadata(path, frame_index=2)

    assert metadata.format == "tiff"
    assert metadata.frame_index == 2
    assert metadata.geometry.width == 640
    assert metadata.geometry.height == 480
    assert metadata.geometry.bit_depth == 16
    assert metadata.geometry.channel_count == 1
    assert metadata.capture.captured_at_utc == "2026:07:14 04:00:00"


def test_read_frame_metadata_rejects_unknown_suffix(tmp_path) -> None:
    path = tmp_path / "frame.xyz"
    path.write_text("nope")

    with pytest.raises(ValueError, match="unsupported frame format"):
        read_frame_metadata(path)


def _write_minimal_fits(path, values) -> None:
    cards = [_fits_card(key, value) for key, value in values.items()]
    cards.append("END".ljust(80))
    header = "".join(cards).encode("ascii")
    padding = b" " * ((2880 - (len(header) % 2880)) % 2880)
    path.write_bytes(header + padding)


def _fits_card(key, value) -> str:
    if isinstance(value, bool):
        rendered = "T" if value else "F"
    elif isinstance(value, str):
        rendered = f"'{value}'"
    else:
        rendered = str(value)
    return f"{key:<8}= {rendered:<20}".ljust(80)


def _minimal_tiff(*, width: int, height: int, bit_depth: int, samples: int) -> bytes:
    endian = "<"
    header = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)
    entries = [
        _tiff_entry(256, 4, 1, width, endian),
        _tiff_entry(257, 4, 1, height, endian),
        _tiff_entry(258, 3, 1, bit_depth, endian),
        _tiff_entry(277, 3, 1, samples, endian),
    ]
    date = b"2026:07:14 04:00:00\x00"
    date_offset = 8 + 2 + (len(entries) + 1) * 12 + 4
    entries.append(_tiff_entry(306, 2, len(date), date_offset, endian))
    ifd = struct.pack("<H", len(entries)) + b"".join(entries) + struct.pack("<I", 0)
    return header + ifd + date


def _tiff_entry(tag: int, value_type: int, count: int, value: int, endian: str) -> bytes:
    return struct.pack(endian + "HHII", tag, value_type, count, value)
