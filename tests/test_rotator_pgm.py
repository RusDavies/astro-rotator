from __future__ import annotations

import pytest

from astro_rotator.rotator import PgmImage, read_pgm_image, rotate_pgm_file, rotate_pgm_image


def test_rotate_pgm_image_identity_keeps_pixels() -> None:
    image = PgmImage(
        width=3,
        height=3,
        pixels=((0, 10, 20), (30, 40, 50), (60, 70, 80)),
    )

    rotated = rotate_pgm_image(image, 0.0, interpolation="nearest")

    assert rotated == image


def test_rotate_pgm_image_180_degrees_same_canvas() -> None:
    image = PgmImage(
        width=3,
        height=3,
        pixels=((1, 2, 3), (4, 5, 6), (7, 8, 9)),
    )

    rotated = rotate_pgm_image(image, 180.0, interpolation="nearest")

    assert rotated.pixels == ((9, 8, 7), (6, 5, 4), (3, 2, 1))


def test_rotate_pgm_file_writes_output(tmp_path) -> None:
    input_path = tmp_path / "input.pgm"
    output_path = tmp_path / "out" / "input.pgm"
    input_path.write_bytes(b"P5\n3 3\n255\n" + bytes([1, 2, 3, 4, 5, 6, 7, 8, 9]))

    result = rotate_pgm_file(input_path, output_path, 0.0, interpolation="bilinear")

    assert result.output_path == str(output_path)
    assert result.interpolation == "bilinear"
    assert read_pgm_image(output_path).pixels == ((1, 2, 3), (4, 5, 6), (7, 8, 9))


def test_rotate_pgm_rejects_unsupported_canvas_policy() -> None:
    image = PgmImage(width=1, height=1, pixels=((255,),))

    with pytest.raises(ValueError, match="same-size canvas"):
        rotate_pgm_image(image, 1.0, canvas_policy="expand")  # type: ignore[arg-type]
