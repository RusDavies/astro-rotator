from __future__ import annotations

import pytest

from astro_rotator.evidence import estimate_rotation_from_pgm
from astro_rotator.testdata import SyntheticStackConfig, generate_synthetic_stack


def test_image_registration_estimates_pure_rotation(tmp_path) -> None:
    generate_synthetic_stack(
        tmp_path,
        SyntheticStackConfig(
            seed=101,
            width=96,
            height=96,
            star_count=32,
            noise_sigma=0.2,
            angle_degrees=(0.0, 3.0),
        ),
    )

    estimate = estimate_rotation_from_pgm(tmp_path / "frame_000.pgm", tmp_path / "frame_001.pgm")

    assert estimate.matched_stars >= 20
    assert estimate.rms_error_pixels < 0.8
    assert estimate.rotation_degrees == pytest.approx(3.0, abs=0.25)
    assert estimate.rejected_match_count >= 0
    assert len(estimate.residual_error_pixels) == estimate.matched_stars


def test_image_registration_populates_report_transform_diagnostics(tmp_path) -> None:
    generate_synthetic_stack(
        tmp_path,
        SyntheticStackConfig(
            seed=303,
            width=96,
            height=96,
            star_count=32,
            noise_sigma=0.2,
            angle_degrees=(0.0, 2.5),
        ),
    )

    reference = tmp_path / "frame_000.pgm"
    target = tmp_path / "frame_001.pgm"
    estimate = estimate_rotation_from_pgm(reference, target)

    evidence = estimate.to_angle_evidence(frame_path=target, reference_frame_path=reference)
    payload = evidence.to_dict()

    assert payload["source"] == "image_registration"
    assert payload["status"] == "ok"
    assert payload["evidence_role"] == "selected"
    assert payload["rotation_degrees"] == pytest.approx(2.5, abs=0.25)
    assert payload["derotation_degrees"] == pytest.approx(-2.5, abs=0.25)
    diagnostics = payload["transform_diagnostics"]
    assert diagnostics["transform_model"] == "similarity_2d"
    assert diagnostics["inlier_count"] == estimate.matched_stars
    assert diagnostics["rejected_match_count"] == estimate.rejected_match_count
    assert diagnostics["rms_error_pixels"] == estimate.rms_error_pixels
    assert diagnostics["residual_summary"]["count"] == estimate.matched_stars
    assert diagnostics["preprocessing"]["star_detector"] == "local_maxima_centroid"
    assert diagnostics["parameters"]["translation_pixels"] == list(estimate.translation_pixels)


def test_image_registration_estimates_rotation_and_translation(tmp_path) -> None:
    generate_synthetic_stack(
        tmp_path,
        SyntheticStackConfig(
            seed=202,
            width=112,
            height=96,
            star_count=36,
            noise_sigma=0.2,
            angle_degrees=(0.0, -2.0),
            translation_pixels=((0.0, 0.0), (3.0, -2.0)),
        ),
    )

    estimate = estimate_rotation_from_pgm(tmp_path / "frame_000.pgm", tmp_path / "frame_001.pgm")

    assert estimate.matched_stars >= 20
    assert estimate.rms_error_pixels < 1.0
    assert estimate.rotation_degrees == pytest.approx(-2.0, abs=0.25)
    assert estimate.translation_pixels[0] == pytest.approx(3.0, abs=0.8)
    assert estimate.translation_pixels[1] == pytest.approx(-2.0, abs=0.8)


def test_image_registration_rejects_empty_frames(tmp_path) -> None:
    empty = tmp_path / "empty.pgm"
    empty.write_bytes(b"P5\n8 8\n255\n" + bytes(64))

    with pytest.raises(ValueError, match="at least two detected stars"):
        estimate_rotation_from_pgm(empty, empty)
