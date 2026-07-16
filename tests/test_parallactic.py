from __future__ import annotations

import math
from datetime import UTC, datetime

from astro_rotator.angle_model import (
    EquatorialGeometrySample,
    GeometrySample,
    geometry_rotation_estimates,
    geometry_sample_from_equatorial,
    julian_date_from_utc,
    local_sidereal_time_degrees,
    normalize_degrees,
    parallactic_angle_degrees,
)
from astro_rotator.testdata import SyntheticStackConfig, generate_synthetic_stack


def test_parallactic_angle_is_zero_on_meridian_for_equatorial_target() -> None:
    sample = GeometrySample(
        hour_angle_degrees=0.0,
        latitude_degrees=45.0,
        declination_degrees=0.0,
    )

    assert parallactic_angle_degrees(sample) == 0.0


def test_parallactic_angle_has_expected_sign_across_meridian() -> None:
    east = GeometrySample(
        hour_angle_degrees=-15.0,
        latitude_degrees=45.0,
        declination_degrees=0.0,
    )
    west = GeometrySample(
        hour_angle_degrees=15.0,
        latitude_degrees=45.0,
        declination_degrees=0.0,
    )

    assert parallactic_angle_degrees(east) < 0.0
    assert parallactic_angle_degrees(west) > 0.0
    assert math.isclose(
        parallactic_angle_degrees(east),
        -parallactic_angle_degrees(west),
        abs_tol=1e-12,
    )


def test_geometry_rotation_estimates_report_relative_rotation_and_compensation() -> None:
    reference = GeometrySample(
        hour_angle_degrees=0.0,
        latitude_degrees=45.0,
        declination_degrees=0.0,
    )
    samples = (
        reference,
        GeometrySample(
            hour_angle_degrees=15.0,
            latitude_degrees=45.0,
            declination_degrees=0.0,
        ),
    )

    estimates = geometry_rotation_estimates(reference, samples)

    assert estimates[0].relative_field_rotation_degrees == 0.0
    assert estimates[0].image_rotation_degrees == 0.0
    assert estimates[0].derotation_degrees == 0.0
    assert math.isclose(estimates[1].relative_field_rotation_degrees, 14.5108187, abs_tol=1e-7)
    assert estimates[1].image_rotation_degrees == estimates[1].relative_field_rotation_degrees
    assert estimates[1].derotation_degrees == -estimates[1].image_rotation_degrees


def test_j2000_timestamp_converts_to_local_sidereal_time() -> None:
    captured_at = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)

    assert julian_date_from_utc(captured_at) == 2451545.0
    assert math.isclose(
        local_sidereal_time_degrees(captured_at, observer_longitude_degrees=0.0),
        280.46061837,
        abs_tol=1e-8,
    )


def test_equatorial_geometry_converts_to_hour_angle_sample() -> None:
    captured_at = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)
    sample = geometry_sample_from_equatorial(
        EquatorialGeometrySample(
            captured_at_utc=captured_at,
            observer_longitude_degrees=-75.0,
            target_right_ascension_degrees=205.46061837,
            latitude_degrees=45.0,
            declination_degrees=0.0,
        )
    )

    assert math.isclose(sample.hour_angle_degrees, 0.0, abs_tol=1e-8)
    assert sample.latitude_degrees == 45.0
    assert sample.declination_degrees == 0.0


def test_geometry_angles_can_drive_synthetic_truth_manifest(tmp_path) -> None:
    reference = GeometrySample(
        hour_angle_degrees=0.0,
        latitude_degrees=45.0,
        declination_degrees=0.0,
    )
    samples = (
        reference,
        GeometrySample(
            hour_angle_degrees=7.5,
            latitude_degrees=45.0,
            declination_degrees=0.0,
        ),
        GeometrySample(
            hour_angle_degrees=15.0,
            latitude_degrees=45.0,
            declination_degrees=0.0,
        ),
    )
    estimates = geometry_rotation_estimates(reference, samples)
    expected_angles = tuple(estimate.image_rotation_degrees for estimate in estimates)

    manifest = generate_synthetic_stack(
        tmp_path,
        SyntheticStackConfig(
            name="geometry_driven_seed_42",
            width=64,
            height=64,
            star_count=24,
            angle_degrees=expected_angles,
        ),
    )

    manifest_angles = tuple(frame["angle_degrees_from_reference"] for frame in manifest["frames"])
    assert manifest_angles == expected_angles


def test_normalize_degrees_wraps_to_signed_range() -> None:
    assert normalize_degrees(0.0) == 0.0
    assert normalize_degrees(181.0) == -179.0
    assert normalize_degrees(-181.0) == 179.0
    assert normalize_degrees(540.0) == 180.0
