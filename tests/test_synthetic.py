from __future__ import annotations

import json

import pytest

from astro_rotator.testdata import SCHEMA, SyntheticStackConfig, generate_synthetic_stack


def test_generate_synthetic_stack_writes_manifest_and_frames(tmp_path) -> None:
    config = SyntheticStackConfig(
        name="rotation_translation_seed_7",
        seed=7,
        width=64,
        height=48,
        star_count=20,
        angle_degrees=(0.0, 0.5, 1.0),
        translation_pixels=((0.0, 0.0), (1.0, -0.5), (2.0, -1.0)),
    )

    manifest = generate_synthetic_stack(tmp_path, config)

    assert manifest["schema"] == SCHEMA
    assert manifest["reference_frame"] == "frame_000.pgm"
    assert [frame["path"] for frame in manifest["frames"]] == [
        "frame_000.pgm",
        "frame_001.pgm",
        "frame_002.pgm",
    ]
    assert manifest["frames"][1]["angle_degrees_from_reference"] == 0.5
    assert manifest["frames"][1]["translation_pixels_from_reference"] == [1.0, -0.5]
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "frame_000.pgm").read_bytes().startswith(b"P5\n64 48\n255\n")


def test_generate_synthetic_stack_is_deterministic(tmp_path) -> None:
    config = SyntheticStackConfig(
        seed=99,
        width=32,
        height=32,
        star_count=12,
        noise_sigma=0.5,
        angle_degrees=(0.0, 1.25),
        hot_pixel_count=2,
    )
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first_manifest = generate_synthetic_stack(first_dir, config)
    second_manifest = generate_synthetic_stack(second_dir, config)

    assert first_manifest == second_manifest
    assert (first_dir / "manifest.json").read_text() == (second_dir / "manifest.json").read_text()
    assert (first_dir / "frame_000.pgm").read_bytes() == (second_dir / "frame_000.pgm").read_bytes()
    assert (first_dir / "frame_001.pgm").read_bytes() == (second_dir / "frame_001.pgm").read_bytes()


def test_manifest_file_matches_returned_manifest(tmp_path) -> None:
    manifest = generate_synthetic_stack(tmp_path, SyntheticStackConfig())

    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"width": 0}, "width and height"),
        ({"star_count": 0}, "star_count"),
        ({"psf_sigma": 0.0}, "psf_sigma"),
        ({"missing_star_fraction": 1.5}, "missing_star_fraction"),
    ],
)
def test_config_validation(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        SyntheticStackConfig(**kwargs)
