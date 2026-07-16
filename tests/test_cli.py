from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from astro_rotator.angle_model import GeometrySample, geometry_rotation_estimates
from astro_rotator.cli import app
from astro_rotator.frame_catalog import read_frame_metadata
from astro_rotator.testdata import SyntheticStackConfig, generate_synthetic_stack


def test_cli_no_args_shows_version() -> None:
    result = CliRunner().invoke(app, [])

    assert result.exit_code == 0
    assert "astro-rotator 0.1.0" in result.output


def test_derotate_writes_outputs_and_evidence_report(tmp_path) -> None:
    input_dir = tmp_path / "frames"
    output_dir = tmp_path / "out"
    generate_synthetic_stack(
        input_dir,
        SyntheticStackConfig(
            seed=404,
            width=96,
            height=96,
            star_count=32,
            noise_sigma=0.2,
            angle_degrees=(0.0, 1.5),
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "derotate",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--reference",
            "frame_001.pgm",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Derotated 2 frame(s)" in result.output
    assert (output_dir / "frame_000.pgm").is_file()
    assert (output_dir / "frame_001.pgm").is_file()
    assert read_frame_metadata(output_dir / "frame_001.pgm").geometry.width == 96

    report = json.loads((output_dir / "angle-evidence-report.json").read_text())
    assert report["schema"] == "astro-rotator.angle-evidence-report.v1"
    assert report["reference_frame_path"].endswith("frame_001.pgm")
    assert len(report["frames"]) == 2
    assert report["frames"][0]["selected_source"] == "image_registration"
    assert report["frames"][1]["selected_rotation_degrees"] == 0.0
    assert report["frames"][0]["evidence"][0]["source"] == "image_registration"
    assert "transform_diagnostics" in report["frames"][0]["evidence"][0]
    assert "derotation_output" in report["frames"][0]["evidence"][0]["diagnostics"]


def test_derotate_reference_index(tmp_path) -> None:
    input_dir = tmp_path / "frames"
    output_dir = tmp_path / "out"
    generate_synthetic_stack(
        input_dir,
        SyntheticStackConfig(
            seed=405,
            width=96,
            height=96,
            star_count=32,
            noise_sigma=0.2,
            angle_degrees=(0.0, 1.5),
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "derotate",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--reference",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads((output_dir / "angle-evidence-report.json").read_text())
    assert report["reference_frame_path"].endswith("frame_001.pgm")


def test_derotate_uses_direct_geometry_angle_flags(tmp_path) -> None:
    input_dir = tmp_path / "frames"
    output_dir = tmp_path / "out"
    samples = (
        GeometrySample(hour_angle_degrees=0.0, latitude_degrees=45.0, declination_degrees=0.0),
        GeometrySample(hour_angle_degrees=7.5, latitude_degrees=45.0, declination_degrees=0.0),
    )
    estimates = geometry_rotation_estimates(samples[0], samples)
    generate_synthetic_stack(
        input_dir,
        SyntheticStackConfig(
            seed=406,
            width=96,
            height=96,
            star_count=32,
            noise_sigma=0.2,
            angle_degrees=tuple(estimate.image_rotation_degrees for estimate in estimates),
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "derotate",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--angle-source",
            "geometry",
            "--geometry-hour-angles",
            "0.0,7.5",
            "--geometry-latitude",
            "45.0",
            "--geometry-declination",
            "0.0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (output_dir / "frame_001.pgm").is_file()
    report = json.loads((output_dir / "angle-evidence-report.json").read_text())
    assert report["assumptions"][-1] == "geometry_selected_for_pgm_inputs"
    second_frame = report["frames"][1]
    assert second_frame["selected_source"] == "geometry"
    assert second_frame["selected_rotation_degrees"] == pytest.approx(
        estimates[1].image_rotation_degrees
    )
    assert second_frame["selected_derotation_degrees"] == pytest.approx(
        estimates[1].derotation_degrees
    )
    assert second_frame["evidence"][0]["method"] == "parallactic_angle_direct_hour_angle.v1"
    assert "hour_angle_supplied_directly" in second_frame["evidence"][0]["assumptions"]


def test_derotate_uses_timestamp_location_target_geometry_flags(tmp_path) -> None:
    input_dir = tmp_path / "frames"
    output_dir = tmp_path / "out"
    timestamps = (
        "2000-01-01T12:00:00Z",
        "2000-01-01T12:30:00Z",
    )
    generate_synthetic_stack(
        input_dir,
        SyntheticStackConfig(
            seed=407,
            width=96,
            height=96,
            star_count=32,
            noise_sigma=0.2,
            angle_degrees=(0.0, 5.0),
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "derotate",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--angle-source",
            "geometry",
            "--geometry-timestamps",
            ",".join(timestamps),
            "--geometry-latitude",
            "45.0",
            "--geometry-longitude",
            "-75.0",
            "--geometry-right-ascension",
            "205.46061837",
            "--geometry-declination",
            "0.0",
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads((output_dir / "angle-evidence-report.json").read_text())
    second_frame = report["frames"][1]
    assert second_frame["selected_source"] == "geometry"
    assert second_frame["selected_rotation_degrees"] != 0.0
    assert second_frame["evidence"][0]["method"] == (
        "parallactic_angle_timestamp_location_target.v1"
    )
    assert "longitude_positive_east" in second_frame["evidence"][0]["assumptions"]
    assert (output_dir / "frame_001.pgm").is_file()


def test_derotate_geometry_mode_requires_complete_direct_geometry_inputs(tmp_path) -> None:
    input_dir = tmp_path / "frames"
    generate_synthetic_stack(
        input_dir,
        SyntheticStackConfig(width=32, height=32, star_count=8, angle_degrees=(0.0, 1.0)),
    )

    result = CliRunner().invoke(
        app,
        [
            "derotate",
            "--input",
            str(input_dir),
            "--output",
            str(tmp_path / "out"),
            "--angle-source",
            "geometry",
        ],
    )

    assert result.exit_code != 0
    assert "--angle-source geometry requires --geometry-latitude" in result.output


def test_derotate_rejects_empty_input_directory(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "derotate",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "contains no supported PGM, FITS, or TIFF" in result.output
