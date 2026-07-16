from __future__ import annotations

import math

import pytest

from astro_rotator.evidence import (
    InclinometerCalibration,
    UncertaintyTerm,
    confidence_from_uncertainty,
    offset_from_reference,
)


def test_inclinometer_calibration_applies_offset_polarity_and_scale() -> None:
    offset = offset_from_reference(10.0, 35.0, polarity=-1, scale=0.98)
    calibration = InclinometerCalibration(
        method="single_point_horizon",
        offset_degrees=offset,
        polarity=-1,
        scale=0.98,
        residual_rms_degrees=0.2,
        uncertainty_terms=(
            UncertaintyTerm("sensor_repeatability", 0.1),
            UncertaintyTerm("mounting_flexure", 0.3),
        ),
    )

    assert calibration.calibrated_altitude_degrees(10.0) == pytest.approx(35.0)
    assert calibration.calibrated_altitude_degrees(12.0) == pytest.approx(33.04)
    assert calibration.uncertainty_degrees() == pytest.approx(math.sqrt(0.1**2 + 0.3**2 + 0.2**2))
    assert calibration.confidence() == 0.85
    assert calibration.status() == "ok"


def test_inclinometer_diagnostics_are_report_friendly() -> None:
    calibration = InclinometerCalibration(
        method="plate_solved_altitude",
        offset_degrees=1.5,
        residual_rms_degrees=0.8,
        uncertainty_terms=(UncertaintyTerm("temperature_drift", 0.7, ("night_cooling",)),),
        warnings=("single_session_calibration",),
    )

    diagnostics = calibration.to_diagnostics(42.0)

    assert diagnostics["sensor"] == "scope_mounted_inclinometer"
    assert diagnostics["calibrated_tube_altitude_degrees"] == pytest.approx(43.5)
    assert diagnostics["uncertainty_degrees"] == pytest.approx(math.sqrt(0.7**2 + 0.8**2))
    assert diagnostics["uncertainty_terms"] == [
        {
            "name": "temperature_drift",
            "degrees": 0.7,
            "notes": ["night_cooling"],
        }
    ]
    assert calibration.status() == "warning"


def test_confidence_model_degrades_with_uncertainty() -> None:
    assert confidence_from_uncertainty(0.1) == 0.95
    assert confidence_from_uncertainty(0.5) == 0.85
    assert confidence_from_uncertainty(1.0) == 0.7
    assert confidence_from_uncertainty(2.0) == 0.5
    assert confidence_from_uncertainty(5.0) == 0.25
    assert confidence_from_uncertainty(5.1) == 0.05


def test_inclinometer_rejects_invalid_uncertainty() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        UncertaintyTerm("bad", -0.1)

    with pytest.raises(ValueError, match="scale must be positive"):
        InclinometerCalibration(
            method="factory_or_manual",
            offset_degrees=0.0,
            scale=0.0,
            uncertainty_terms=(),
        )
