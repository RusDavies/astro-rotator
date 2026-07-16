"""Frame metadata model for supported image formats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SupportedImageFormat = Literal["pgm", "fits", "tiff"]


@dataclass(frozen=True)
class FrameGeometry:
    """Image geometry and pixel representation."""

    width: int
    height: int
    bit_depth: int
    channel_count: int = 1
    bayer_pattern: str | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.bit_depth <= 0:
            raise ValueError("bit_depth must be positive")
        if self.channel_count <= 0:
            raise ValueError("channel_count must be positive")


@dataclass(frozen=True)
class CaptureMetadata:
    """Normalized optional capture metadata."""

    captured_at_utc: str | None = None
    exposure_seconds: float | None = None
    camera_name: str | None = None
    telescope_name: str | None = None
    filter_name: str | None = None
    gain: float | None = None
    offset: float | None = None
    sensor_temperature_celsius: float | None = None
    focal_length_mm: float | None = None
    f_number: float | None = None
    iso: int | None = None

    def __post_init__(self) -> None:
        if self.exposure_seconds is not None and self.exposure_seconds < 0:
            raise ValueError("exposure_seconds must not be negative")
        if self.iso is not None and self.iso <= 0:
            raise ValueError("iso must be positive")


@dataclass(frozen=True)
class AstrometryMetadata:
    """Normalized optional sky/location metadata."""

    target_name: str | None = None
    right_ascension_degrees: float | None = None
    declination_degrees: float | None = None
    observer_latitude_degrees: float | None = None
    observer_longitude_degrees: float | None = None
    observer_elevation_meters: float | None = None
    mount_altitude_degrees: float | None = None
    mount_azimuth_degrees: float | None = None


@dataclass(frozen=True)
class FrameMetadata:
    """Normalized metadata for one input frame."""

    path: str
    format: SupportedImageFormat
    geometry: FrameGeometry
    frame_index: int | None = None
    capture: CaptureMetadata = field(default_factory=CaptureMetadata)
    astrometry: AstrometryMetadata = field(default_factory=AstrometryMetadata)
    raw_fields: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "format": self.format,
            "frame_index": self.frame_index,
            "geometry": _without_none(self.geometry.__dict__),
            "capture": _without_none(self.capture.__dict__),
            "astrometry": _without_none(self.astrometry.__dict__),
            "raw_fields": self.raw_fields,
            "warnings": list(self.warnings),
        }


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}
