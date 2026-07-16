"""Parallactic-angle helpers for geometry-derived field rotation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class GeometrySample:
    """A single geometry sample expressed in angular degrees."""

    hour_angle_degrees: float
    latitude_degrees: float
    declination_degrees: float


@dataclass(frozen=True)
class EquatorialGeometrySample:
    """A geometry sample before conversion into hour angle."""

    captured_at_utc: datetime
    observer_longitude_degrees: float
    target_right_ascension_degrees: float
    latitude_degrees: float
    declination_degrees: float


@dataclass(frozen=True)
class RotationEstimate:
    """Geometry-derived rotation relative to a reference sample."""

    parallactic_angle_degrees: float
    relative_field_rotation_degrees: float
    image_rotation_degrees: float
    derotation_degrees: float


def parallactic_angle_degrees(sample: GeometrySample) -> float:
    """Return parallactic angle in degrees for the supplied geometry sample.

    Hour angle is positive westward. The formula used here is:

    q = atan2(sin(H), tan(phi) * cos(delta) - sin(delta) * cos(H))

    Where H is hour angle, phi is observer latitude, and delta is target
    declination. The result is normalized into [-180, 180) degrees.
    """

    hour_angle = math.radians(sample.hour_angle_degrees)
    latitude = math.radians(sample.latitude_degrees)
    declination = math.radians(sample.declination_degrees)

    numerator = math.sin(hour_angle)
    denominator = (math.tan(latitude) * math.cos(declination)) - (
        math.sin(declination) * math.cos(hour_angle)
    )
    return normalize_degrees(math.degrees(math.atan2(numerator, denominator)))


def geometry_sample_from_equatorial(sample: EquatorialGeometrySample) -> GeometrySample:
    """Convert timestamp/location/target coordinates into direct-hour-angle geometry."""

    sidereal_time = local_sidereal_time_degrees(
        sample.captured_at_utc,
        observer_longitude_degrees=sample.observer_longitude_degrees,
    )
    return GeometrySample(
        hour_angle_degrees=normalize_degrees(sidereal_time - sample.target_right_ascension_degrees),
        latitude_degrees=sample.latitude_degrees,
        declination_degrees=sample.declination_degrees,
    )


def local_sidereal_time_degrees(
    captured_at_utc: datetime,
    *,
    observer_longitude_degrees: float,
) -> float:
    """Return local apparent-enough sidereal time in degrees for MVP geometry.

    Longitude is positive eastward. This uses the common compact GMST expression
    relative to J2000.0 and intentionally omits nutation/polar-motion corrections;
    those belong in a later astrometry-grade backend.
    """

    utc_time = captured_at_utc
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=UTC)
    else:
        utc_time = utc_time.astimezone(UTC)
    julian_date = julian_date_from_utc(utc_time)
    days_since_j2000 = julian_date - 2451545.0
    gmst = 280.46061837 + (360.98564736629 * days_since_j2000)
    return normalize_360_degrees(gmst + observer_longitude_degrees)


def julian_date_from_utc(captured_at_utc: datetime) -> float:
    """Return Julian Date for a UTC datetime."""

    utc_time = captured_at_utc.astimezone(UTC)
    year = utc_time.year
    month = utc_time.month
    day = utc_time.day
    if month <= 2:
        year -= 1
        month += 12
    correction_a = year // 100
    correction_b = 2 - correction_a + (correction_a // 4)
    fractional_day = (
        utc_time.hour
        + (utc_time.minute / 60.0)
        + ((utc_time.second + (utc_time.microsecond / 1_000_000.0)) / 3600.0)
    ) / 24.0
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + correction_b
        - 1524.5
        + fractional_day
    )


def geometry_rotation_estimates(
    reference: GeometrySample,
    samples: tuple[GeometrySample, ...],
) -> tuple[RotationEstimate, ...]:
    """Return geometry-derived rotation estimates relative to a reference.

    The provisional image convention matches the synthetic fixture convention:
    positive `image_rotation_degrees` is counterclockwise in displayed image
    coordinates. Later calibration can insert camera parity and optical
    inversion between `relative_field_rotation_degrees` and image-space angle.
    """

    reference_angle = parallactic_angle_degrees(reference)
    estimates: list[RotationEstimate] = []
    for sample in samples:
        angle = parallactic_angle_degrees(sample)
        relative = normalize_degrees(angle - reference_angle)
        image_rotation = relative
        estimates.append(
            RotationEstimate(
                parallactic_angle_degrees=angle,
                relative_field_rotation_degrees=relative,
                image_rotation_degrees=image_rotation,
                derotation_degrees=normalize_degrees(-image_rotation),
            )
        )
    return tuple(estimates)


def normalize_degrees(value: float) -> float:
    """Normalize an angle into [-180, 180) degrees."""

    normalized = (value + 180.0) % 360.0 - 180.0
    if normalized == -180.0 and value > 0:
        return 180.0
    return normalized


def normalize_360_degrees(value: float) -> float:
    """Normalize an angle into [0, 360) degrees."""

    return value % 360.0
