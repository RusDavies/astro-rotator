"""Dependency-light frame metadata readers."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from astro_rotator.frame_catalog.metadata import (
    AstrometryMetadata,
    CaptureMetadata,
    FrameGeometry,
    FrameMetadata,
)


def read_frame_metadata(path: str | Path, *, frame_index: int | None = None) -> FrameMetadata:
    """Read normalized metadata for a supported frame path."""

    frame_path = Path(path)
    suffix = frame_path.suffix.lower()
    if suffix == ".pgm":
        return read_pgm_metadata(frame_path, frame_index=frame_index)
    if suffix in {".fit", ".fits", ".fts"}:
        return read_fits_metadata(frame_path, frame_index=frame_index)
    if suffix in {".tif", ".tiff"}:
        return read_tiff_metadata(frame_path, frame_index=frame_index)
    raise ValueError(f"unsupported frame format: {suffix or '<none>'}")


def read_pgm_metadata(path: str | Path, *, frame_index: int | None = None) -> FrameMetadata:
    """Read geometry metadata from an 8-bit binary PGM/P5 file."""

    frame_path = Path(path)
    tokens, _body_offset = _pgm_header_tokens(frame_path.read_bytes())
    if tokens[0] != b"P5":
        raise ValueError("only binary PGM/P5 images are supported")
    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    if max_value != 255:
        raise ValueError("only 8-bit PGM images are supported")
    return FrameMetadata(
        path=str(frame_path),
        format="pgm",
        frame_index=frame_index,
        geometry=FrameGeometry(width=width, height=height, bit_depth=8),
        warnings=("pgm_contains_no_capture_metadata",),
    )


def read_fits_metadata(path: str | Path, *, frame_index: int | None = None) -> FrameMetadata:
    """Read common metadata from the primary FITS header."""

    frame_path = Path(path)
    header = _read_fits_header(frame_path)
    width = _required_int(header, "NAXIS1")
    height = _required_int(header, "NAXIS2")
    bitpix = _required_int(header, "BITPIX")
    capture = CaptureMetadata(
        captured_at_utc=_first_string(header, ("DATE-OBS", "DATE-BEG", "DATE-END")),
        exposure_seconds=_first_float(header, ("EXPTIME", "EXPOSURE")),
        camera_name=_first_string(header, ("INSTRUME", "CAMERA")),
        telescope_name=_first_string(header, ("TELESCOP",)),
        filter_name=_first_string(header, ("FILTER",)),
        gain=_first_float(header, ("GAIN",)),
        offset=_first_float(header, ("OFFSET",)),
        sensor_temperature_celsius=_first_float(header, ("CCD-TEMP", "SET-TEMP")),
    )
    astrometry = AstrometryMetadata(
        target_name=_first_string(header, ("OBJECT",)),
        right_ascension_degrees=_first_angle(header, ("OBJCTRA", "RA"), hours=True),
        declination_degrees=_first_angle(header, ("OBJCTDEC", "DEC"), hours=False),
        observer_latitude_degrees=_first_float(header, ("SITELAT", "OBSGEO-B")),
        observer_longitude_degrees=_first_float(header, ("SITELONG", "OBSGEO-L")),
        observer_elevation_meters=_first_float(header, ("OBSGEO-H",)),
        mount_altitude_degrees=_first_float(header, ("ALT", "OBJCTALT")),
        mount_azimuth_degrees=_first_float(header, ("AZ", "OBJCTAZ")),
    )
    return FrameMetadata(
        path=str(frame_path),
        format="fits",
        frame_index=frame_index,
        geometry=FrameGeometry(
            width=width,
            height=height,
            bit_depth=abs(bitpix),
            channel_count=max(1, int(header.get("NAXIS3", 1))),
        ),
        capture=capture,
        astrometry=astrometry,
        raw_fields=header,
    )


def read_tiff_metadata(path: str | Path, *, frame_index: int | None = None) -> FrameMetadata:
    """Read basic geometry metadata from a classic TIFF file."""

    frame_path = Path(path)
    tags = _read_tiff_tags(frame_path.read_bytes())
    width = int(tags[256])
    height = int(tags[257])
    bits_per_sample = tags.get(258, 8)
    if isinstance(bits_per_sample, tuple):
        bit_depth = int(bits_per_sample[0])
        channel_count = len(bits_per_sample)
    else:
        bit_depth = int(bits_per_sample)
        channel_count = int(tags.get(277, 1))
    capture = CaptureMetadata(captured_at_utc=tags.get(306))
    return FrameMetadata(
        path=str(frame_path),
        format="tiff",
        frame_index=frame_index,
        geometry=FrameGeometry(
            width=width,
            height=height,
            bit_depth=bit_depth,
            channel_count=channel_count,
        ),
        capture=capture,
        raw_fields={str(key): value for key, value in tags.items()},
    )


def _pgm_header_tokens(data: bytes) -> tuple[list[bytes], int]:
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 4:
        while index < len(data) and data[index] in b" \t\r\n":
            index += 1
        if index < len(data) and data[index] == ord("#"):
            while index < len(data) and data[index] not in b"\r\n":
                index += 1
            continue
        start = index
        while index < len(data) and data[index] not in b" \t\r\n":
            index += 1
        tokens.append(data[start:index])
    if index < len(data) and data[index] in b" \t\r\n":
        index += 1
    return tokens, index


def _read_fits_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    header: dict[str, Any] = {}
    for index in range(0, len(data), 80):
        card = data[index : index + 80].decode("ascii", errors="replace")
        keyword = card[:8].strip()
        if keyword == "END":
            break
        if not keyword or card[8:10] != "= ":
            continue
        value_text = card[10:80].split("/", 1)[0].strip()
        header[keyword] = _parse_fits_value(value_text)
    return header


def _parse_fits_value(value_text: str) -> Any:
    if value_text.startswith("'"):
        end = value_text.find("'", 1)
        return value_text[1:end].strip() if end != -1 else value_text.strip("'")
    if value_text in {"T", "F"}:
        return value_text == "T"
    try:
        if any(char in value_text for char in ".EeDd"):
            return float(value_text.replace("D", "E").replace("d", "e"))
        return int(value_text)
    except ValueError:
        return value_text


def _read_tiff_tags(data: bytes) -> dict[int, Any]:
    if data[:2] == b"II":
        endian = "<"
    elif data[:2] == b"MM":
        endian = ">"
    else:
        raise ValueError("unsupported TIFF byte order")
    magic = struct.unpack(endian + "H", data[2:4])[0]
    if magic != 42:
        raise ValueError("only classic TIFF is supported")
    ifd_offset = struct.unpack(endian + "I", data[4:8])[0]
    count = struct.unpack(endian + "H", data[ifd_offset : ifd_offset + 2])[0]
    tags: dict[int, Any] = {}
    for entry_index in range(count):
        offset = ifd_offset + 2 + (entry_index * 12)
        tag, value_type, value_count, value_or_offset = struct.unpack(
            endian + "HHII",
            data[offset : offset + 12],
        )
        tags[tag] = _read_tiff_value(data, endian, value_type, value_count, value_or_offset)
    return tags


def _read_tiff_value(
    data: bytes,
    endian: str,
    value_type: int,
    value_count: int,
    value_or_offset: int,
) -> Any:
    type_sizes = {2: 1, 3: 2, 4: 4}
    size = type_sizes.get(value_type)
    if size is None:
        return value_or_offset
    total_size = size * value_count
    if total_size <= 4:
        raw = struct.pack(endian + "I", value_or_offset)[:total_size]
    else:
        raw = data[value_or_offset : value_or_offset + total_size]
    if value_type == 2:
        return raw.rstrip(b"\x00").decode("ascii", errors="replace")
    if value_type == 3:
        values = struct.unpack(endian + ("H" * value_count), raw)
    else:
        values = struct.unpack(endian + ("I" * value_count), raw)
    return values[0] if len(values) == 1 else values


def _required_int(header: dict[str, Any], key: str) -> int:
    if key not in header:
        raise ValueError(f"FITS header missing {key}")
    return int(header[key])


def _first_string(header: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in header:
            return str(header[key])
    return None


def _first_float(header: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in header:
            return float(header[key])
    return None


def _first_angle(
    header: dict[str, Any],
    keys: tuple[str, ...],
    *,
    hours: bool,
) -> float | None:
    for key in keys:
        if key in header:
            return _angle_to_degrees(header[key], hours=hours)
    return None


def _angle_to_degrees(value: Any, *, hours: bool) -> float:
    if isinstance(value, int | float):
        return float(value) * (15.0 if hours else 1.0)
    text = str(value).strip()
    if ":" not in text:
        return float(text) * (15.0 if hours else 1.0)
    sign = -1.0 if text.startswith("-") else 1.0
    parts = text.lstrip("+-").split(":")
    primary = float(parts[0])
    minutes = float(parts[1]) if len(parts) > 1 else 0.0
    seconds = float(parts[2]) if len(parts) > 2 else 0.0
    degrees = primary + (minutes / 60.0) + (seconds / 3600.0)
    if hours:
        degrees *= 15.0
    return sign * degrees
