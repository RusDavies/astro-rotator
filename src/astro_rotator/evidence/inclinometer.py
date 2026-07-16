"""Scope-mounted inclinometer calibration and confidence helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

CalibrationMethod = Literal[
    "single_point_horizon",
    "two_point_altitude",
    "plate_solved_altitude",
    "factory_or_manual",
]

ConfidenceStatus = Literal["ok", "warning", "failed"]


@dataclass(frozen=True)
class UncertaintyTerm:
    """One independent angular uncertainty contribution."""

    name: str
    degrees: float
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("uncertainty term name is required")
        if not math.isfinite(self.degrees) or self.degrees < 0.0:
            raise ValueError("uncertainty term degrees must be finite and non-negative")


@dataclass(frozen=True)
class InclinometerCalibration:
    """Convert a raw inclinometer tilt reading into telescope tube altitude."""

    method: CalibrationMethod
    offset_degrees: float
    uncertainty_terms: tuple[UncertaintyTerm, ...]
    polarity: Literal[-1, 1] = 1
    scale: float = 1.0
    residual_rms_degrees: float | None = None
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_finite(self.offset_degrees, "offset_degrees")
        _validate_finite(self.scale, "scale")
        if self.scale <= 0.0:
            raise ValueError("scale must be positive")
        if self.residual_rms_degrees is not None:
            if not math.isfinite(self.residual_rms_degrees) or self.residual_rms_degrees < 0.0:
                raise ValueError("residual_rms_degrees must be finite and non-negative")

    def calibrated_altitude_degrees(self, raw_tilt_degrees: float) -> float:
        """Return tube altitude from a raw sensor tilt angle."""

        _validate_finite(raw_tilt_degrees, "raw_tilt_degrees")
        return (self.polarity * self.scale * raw_tilt_degrees) + self.offset_degrees

    def uncertainty_degrees(self) -> float:
        """Combine independent uncertainty terms with calibration residual."""

        components = [term.degrees for term in self.uncertainty_terms]
        if self.residual_rms_degrees is not None:
            components.append(self.residual_rms_degrees)
        return math.sqrt(sum(component * component for component in components))

    def confidence(self) -> float:
        """Map total angular uncertainty to a report-friendly confidence score."""

        return confidence_from_uncertainty(self.uncertainty_degrees())

    def status(self) -> ConfidenceStatus:
        uncertainty = self.uncertainty_degrees()
        if uncertainty > 5.0:
            return "failed"
        if uncertainty > 1.0 or self.warnings:
            return "warning"
        return "ok"

    def to_diagnostics(self, raw_tilt_degrees: float) -> dict[str, object]:
        """Return diagnostics suitable for an orientation_sensor evidence entry."""

        return {
            "sensor": "scope_mounted_inclinometer",
            "calibration_method": self.method,
            "raw_tilt_degrees": raw_tilt_degrees,
            "calibrated_tube_altitude_degrees": self.calibrated_altitude_degrees(raw_tilt_degrees),
            "offset_degrees": self.offset_degrees,
            "polarity": self.polarity,
            "scale": self.scale,
            "residual_rms_degrees": self.residual_rms_degrees,
            "uncertainty_degrees": self.uncertainty_degrees(),
            "uncertainty_terms": [
                {
                    "name": term.name,
                    "degrees": term.degrees,
                    "notes": list(term.notes),
                }
                for term in self.uncertainty_terms
            ],
        }


def offset_from_reference(
    raw_tilt_degrees: float,
    known_altitude_degrees: float,
    *,
    polarity: Literal[-1, 1] = 1,
    scale: float = 1.0,
) -> float:
    """Compute a linear offset from one known raw/altitude reference point."""

    _validate_finite(raw_tilt_degrees, "raw_tilt_degrees")
    _validate_finite(known_altitude_degrees, "known_altitude_degrees")
    _validate_finite(scale, "scale")
    if scale <= 0.0:
        raise ValueError("scale must be positive")
    return known_altitude_degrees - (polarity * scale * raw_tilt_degrees)


def confidence_from_uncertainty(uncertainty_degrees: float) -> float:
    """Convert total angular uncertainty into a bounded confidence score."""

    if not math.isfinite(uncertainty_degrees) or uncertainty_degrees < 0.0:
        raise ValueError("uncertainty_degrees must be finite and non-negative")
    if uncertainty_degrees <= 0.25:
        return 0.95
    if uncertainty_degrees <= 0.5:
        return 0.85
    if uncertainty_degrees <= 1.0:
        return 0.7
    if uncertainty_degrees <= 2.0:
        return 0.5
    if uncertainty_degrees <= 5.0:
        return 0.25
    return 0.05


def _validate_finite(value: float, field_name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
