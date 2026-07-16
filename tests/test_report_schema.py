from __future__ import annotations

import json

import pytest

from astro_rotator.reporting import (
    SCHEMA,
    AngleEvidence,
    AngleEvidenceReport,
    FrameAngleReport,
    TransformDiagnostics,
)


def test_angle_evidence_report_serializes_selected_and_supporting_evidence() -> None:
    geometry = AngleEvidence(
        source="geometry",
        status="ok",
        frame_path="frame_001.pgm",
        reference_frame_path="frame_000.pgm",
        rotation_degrees=1.5,
        derotation_degrees=-1.5,
        uncertainty_degrees=0.2,
        confidence=0.75,
        method="parallactic_angle.v1",
        assumptions=("hour_angle_supplied_directly",),
    )
    registration = AngleEvidence(
        source="image_registration",
        status="ok",
        frame_path="frame_001.pgm",
        reference_frame_path="frame_000.pgm",
        rotation_degrees=1.45,
        derotation_degrees=-1.45,
        uncertainty_degrees=0.1,
        confidence=0.9,
        method="synthetic_pairwise_star_fit.v1",
        evidence_role="selected",
        transform_diagnostics=TransformDiagnostics(
            transform_model="similarity_2d",
            inlier_count=28,
            rejected_match_count=3,
            rms_error_pixels=0.42,
            residual_summary={"median_pixels": 0.31, "p95_pixels": 0.72},
            preprocessing={"source": "synthetic_pgm", "stretch": "none"},
            parameters={
                "rotation_degrees": 1.45,
                "translation_pixels": [0.2, -0.1],
            },
        ),
        diagnostics={"matched_stars": 28, "rms_error_pixels": 0.42},
    )
    report = AngleEvidenceReport(
        reference_frame_path="frame_000.pgm",
        coordinate_convention={
            "origin": "top_left",
            "x_positive": "right",
            "y_positive": "down",
            "positive_rotation": "counterclockwise_image_space",
        },
        assumptions=("synthetic_fixture",),
        frames=(
            FrameAngleReport(
                frame_path="frame_001.pgm",
                selected_rotation_degrees=1.45,
                selected_derotation_degrees=-1.45,
                selected_source="image_registration",
                evidence=(geometry, registration),
            ),
        ),
    )

    payload = report.to_dict()

    assert payload["schema"] == SCHEMA
    assert payload["frames"][0]["selected_source"] == "image_registration"
    assert payload["frames"][0]["evidence"][0]["source"] == "geometry"
    assert payload["frames"][0]["evidence"][1]["diagnostics"]["matched_stars"] == 28
    transform = payload["frames"][0]["evidence"][1]["transform_diagnostics"]
    assert payload["frames"][0]["evidence"][1]["evidence_role"] == "selected"
    assert transform["transform_model"] == "similarity_2d"
    assert transform["inlier_count"] == 28
    assert transform["rejected_match_count"] == 3
    assert transform["residual_summary"]["p95_pixels"] == 0.72
    assert transform["preprocessing"]["stretch"] == "none"
    assert json.loads(report.to_json()) == payload


def test_ok_evidence_requires_rotation() -> None:
    with pytest.raises(ValueError, match="ok evidence"):
        AngleEvidence(
            source="geometry",
            status="ok",
            frame_path="frame_001.pgm",
            rotation_degrees=None,
            derotation_degrees=None,
            method="parallactic_angle.v1",
        )


def test_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValueError, match="confidence"):
        AngleEvidence(
            source="image_registration",
            status="warning",
            frame_path="frame_001.pgm",
            rotation_degrees=1.0,
            derotation_degrees=-1.0,
            confidence=1.2,
            method="synthetic_pairwise_star_fit.v1",
        )


def test_selected_source_must_exist_on_frame() -> None:
    with pytest.raises(ValueError, match="selected_source"):
        FrameAngleReport(
            frame_path="frame_001.pgm",
            selected_rotation_degrees=1.0,
            selected_derotation_degrees=-1.0,
            selected_source="image_registration",
            evidence=(
                AngleEvidence(
                    source="geometry",
                    status="ok",
                    frame_path="frame_001.pgm",
                    rotation_degrees=1.0,
                    derotation_degrees=-1.0,
                    method="parallactic_angle.v1",
                ),
            ),
        )


def test_transform_diagnostics_validates_counts_and_residuals() -> None:
    with pytest.raises(ValueError, match="inlier_count"):
        TransformDiagnostics(transform_model="similarity_2d", inlier_count=-1)

    with pytest.raises(ValueError, match="rms_error_pixels"):
        TransformDiagnostics(transform_model="similarity_2d", rms_error_pixels=-0.1)

    with pytest.raises(ValueError, match="transform_model"):
        TransformDiagnostics(transform_model="")
