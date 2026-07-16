"""Angle evidence report schema."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA = "astro-rotator.angle-evidence-report.v1"

EvidenceSource = Literal[
    "geometry",
    "image_registration",
    "metadata",
    "mount_telemetry",
    "orientation_sensor",
]
EvidenceStatus = Literal["ok", "warning", "failed", "not_available"]
EvidenceRole = Literal["selected", "fallback", "advisory", "rejected"]


@dataclass(frozen=True)
class TransformDiagnostics:
    """Diagnostics for an image transform estimated from evidence."""

    transform_model: str
    inlier_count: int | None = None
    rejected_match_count: int | None = None
    rms_error_pixels: float | None = None
    residual_summary: dict[str, float] = field(default_factory=dict)
    preprocessing: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.transform_model:
            raise ValueError("transform_model must not be empty")
        _validate_optional_count(self.inlier_count, "inlier_count")
        _validate_optional_count(self.rejected_match_count, "rejected_match_count")
        _validate_optional_pixels(self.rms_error_pixels, "rms_error_pixels")
        for key, value in self.residual_summary.items():
            _validate_optional_pixels(value, f"residual_summary.{key}")

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "transform_model": self.transform_model,
                "inlier_count": self.inlier_count,
                "rejected_match_count": self.rejected_match_count,
                "rms_error_pixels": self.rms_error_pixels,
                "residual_summary": self.residual_summary,
                "preprocessing": self.preprocessing,
                "parameters": self.parameters,
            }
        )


@dataclass(frozen=True)
class AngleEvidence:
    """One source's angle estimate for one frame."""

    source: EvidenceSource
    status: EvidenceStatus
    frame_path: str
    rotation_degrees: float | None
    derotation_degrees: float | None
    method: str
    confidence: float | None = None
    uncertainty_degrees: float | None = None
    reference_frame_path: str | None = None
    evidence_role: EvidenceRole | None = None
    transform_diagnostics: TransformDiagnostics | None = None
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_optional_degrees(self.rotation_degrees, "rotation_degrees")
        _validate_optional_degrees(self.derotation_degrees, "derotation_degrees")
        _validate_optional_degrees(self.uncertainty_degrees, "uncertainty_degrees")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status == "ok" and self.rotation_degrees is None:
            raise ValueError("ok evidence must include rotation_degrees")

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "source": self.source,
                "status": self.status,
                "frame_path": self.frame_path,
                "reference_frame_path": self.reference_frame_path,
                "rotation_degrees": self.rotation_degrees,
                "derotation_degrees": self.derotation_degrees,
                "uncertainty_degrees": self.uncertainty_degrees,
                "confidence": self.confidence,
                "method": self.method,
                "evidence_role": self.evidence_role,
                "transform_diagnostics": (
                    self.transform_diagnostics.to_dict()
                    if self.transform_diagnostics is not None
                    else None
                ),
                "assumptions": list(self.assumptions),
                "warnings": list(self.warnings),
                "diagnostics": self.diagnostics,
            }
        )


@dataclass(frozen=True)
class FrameAngleReport:
    """Selected angle and all evidence for one frame."""

    frame_path: str
    selected_rotation_degrees: float | None
    selected_derotation_degrees: float | None
    selected_source: EvidenceSource | None
    evidence: tuple[AngleEvidence, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_optional_degrees(self.selected_rotation_degrees, "selected_rotation_degrees")
        _validate_optional_degrees(
            self.selected_derotation_degrees,
            "selected_derotation_degrees",
        )
        if self.selected_source is not None and not any(
            evidence.source == self.selected_source for evidence in self.evidence
        ):
            raise ValueError("selected_source must refer to an evidence source on this frame")

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "frame_path": self.frame_path,
                "selected_rotation_degrees": self.selected_rotation_degrees,
                "selected_derotation_degrees": self.selected_derotation_degrees,
                "selected_source": self.selected_source,
                "evidence": [evidence.to_dict() for evidence in self.evidence],
                "warnings": list(self.warnings),
            }
        )


@dataclass(frozen=True)
class AngleEvidenceReport:
    """Machine-readable report of selected angles and supporting evidence."""

    reference_frame_path: str
    frames: tuple[FrameAngleReport, ...]
    coordinate_convention: dict[str, str]
    schema: str = SCHEMA
    generated_by: str = "astro-rotator"
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError(f"schema must be {SCHEMA}")
        if not self.frames:
            raise ValueError("report must include at least one frame")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_by": self.generated_by,
            "reference_frame_path": self.reference_frame_path,
            "coordinate_convention": self.coordinate_convention,
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "frames": [frame.to_dict() for frame in self.frames],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def _validate_optional_degrees(value: float | None, field_name: str) -> None:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")


def _validate_optional_count(value: int | None, field_name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must not be negative")


def _validate_optional_pixels(value: float | None, field_name: str) -> None:
    if value is not None and (not math.isfinite(value) or value < 0.0):
        raise ValueError(f"{field_name} must be finite and non-negative")


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}
