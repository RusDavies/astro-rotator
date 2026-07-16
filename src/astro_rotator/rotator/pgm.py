"""Dependency-light PGM rotation and derotation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

InterpolationMode = Literal["nearest", "bilinear"]
CanvasPolicy = Literal["same"]


@dataclass(frozen=True)
class PgmImage:
    """An 8-bit binary PGM image held as row-major pixels."""

    width: int
    height: int
    pixels: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if len(self.pixels) != self.height:
            raise ValueError("pixel row count must match height")
        for row in self.pixels:
            if len(row) != self.width:
                raise ValueError("pixel column count must match width")
            if any(value < 0 or value > 255 for value in row):
                raise ValueError("PGM pixels must be 8-bit values")


@dataclass(frozen=True)
class DerotationOutput:
    """Metadata for one written derotated output frame."""

    output_path: str
    derotation_degrees: float
    interpolation: InterpolationMode
    canvas_policy: CanvasPolicy
    fill_value: int
    width: int
    height: int


def read_pgm_image(path: str | Path) -> PgmImage:
    """Read an 8-bit binary PGM/P5 image."""

    image_path = Path(path)
    data = image_path.read_bytes()
    tokens, body_offset = _pgm_header_tokens(data)
    if tokens[0] != b"P5":
        raise ValueError("only binary PGM/P5 images are supported")
    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    if max_value != 255:
        raise ValueError("only 8-bit PGM images are supported")
    expected = width * height
    body = data[body_offset : body_offset + expected]
    if len(body) != expected:
        raise ValueError("PGM image body has unexpected length")
    rows = tuple(tuple(body[row * width : (row + 1) * width]) for row in range(height))
    return PgmImage(width=width, height=height, pixels=rows)


def write_pgm_image(path: str | Path, image: PgmImage) -> None:
    """Write an 8-bit binary PGM/P5 image."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = f"P5\n{image.width} {image.height}\n255\n".encode("ascii")
    body = bytes(value for row in image.pixels for value in row)
    output_path.write_bytes(header + body)


def rotate_pgm_image(
    image: PgmImage,
    angle_degrees: float,
    *,
    interpolation: InterpolationMode = "bilinear",
    canvas_policy: CanvasPolicy = "same",
    fill_value: int = 0,
) -> PgmImage:
    """Rotate an image-space PGM frame by ``angle_degrees``.

    Positive angles follow the project convention: counterclockwise in displayed
    image coordinates, where x increases rightward and y increases downward.
    """

    if canvas_policy != "same":
        raise ValueError("only same-size canvas output is currently supported")
    if interpolation not in {"nearest", "bilinear"}:
        raise ValueError("interpolation must be 'nearest' or 'bilinear'")
    if fill_value < 0 or fill_value > 255:
        raise ValueError("fill_value must be an 8-bit value")

    pivot = ((image.width - 1) / 2.0, (image.height - 1) / 2.0)
    rows: list[tuple[int, ...]] = []
    for y in range(image.height):
        row: list[int] = []
        for x in range(image.width):
            source_x, source_y = _rotate_about_pivot(x, y, -angle_degrees, pivot)
            if interpolation == "nearest":
                row.append(_sample_nearest(image, source_x, source_y, fill_value=fill_value))
            else:
                row.append(_sample_bilinear(image, source_x, source_y, fill_value=fill_value))
        rows.append(tuple(row))
    return PgmImage(width=image.width, height=image.height, pixels=tuple(rows))


def rotate_pgm_file(
    input_path: str | Path,
    output_path: str | Path,
    angle_degrees: float,
    *,
    interpolation: InterpolationMode = "bilinear",
    canvas_policy: CanvasPolicy = "same",
    fill_value: int = 0,
) -> DerotationOutput:
    """Read, rotate, and write one PGM frame."""

    image = read_pgm_image(input_path)
    rotated = rotate_pgm_image(
        image,
        angle_degrees,
        interpolation=interpolation,
        canvas_policy=canvas_policy,
        fill_value=fill_value,
    )
    write_pgm_image(output_path, rotated)
    return DerotationOutput(
        output_path=str(output_path),
        derotation_degrees=angle_degrees,
        interpolation=interpolation,
        canvas_policy=canvas_policy,
        fill_value=fill_value,
        width=rotated.width,
        height=rotated.height,
    )


def _pgm_header_tokens(data: bytes) -> tuple[list[bytes], int]:
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 4:
        while index < len(data) and data[index] in b" \t\r\n":
            index += 1
        if index < len(data) and data[index] == ord("#"):
            while index < len(data) and data[index] not in b"\r\n":
                index += 1
            continue
        start = index
        while index < len(data) and data[index] not in b" \t\r\n":
            index += 1
        tokens.append(data[start:index])
    if index < len(data) and data[index] in b" \t\r\n":
        index += 1
    return tokens, index


def _rotate_about_pivot(
    x: float,
    y: float,
    angle_degrees: float,
    pivot: tuple[float, float],
) -> tuple[float, float]:
    theta = math.radians(angle_degrees)
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)
    dx = x - pivot[0]
    dy = y - pivot[1]
    return (
        pivot[0] + (cos_theta * dx) + (sin_theta * dy),
        pivot[1] - (sin_theta * dx) + (cos_theta * dy),
    )


def _sample_nearest(image: PgmImage, x: float, y: float, *, fill_value: int) -> int:
    nearest_x = round(x)
    nearest_y = round(y)
    if nearest_x < 0 or nearest_x >= image.width or nearest_y < 0 or nearest_y >= image.height:
        return fill_value
    return image.pixels[nearest_y][nearest_x]


def _sample_bilinear(image: PgmImage, x: float, y: float, *, fill_value: int) -> int:
    if x < 0.0 or x > image.width - 1 or y < 0.0 or y > image.height - 1:
        return fill_value
    x0 = math.floor(x)
    y0 = math.floor(y)
    x1 = min(x0 + 1, image.width - 1)
    y1 = min(y0 + 1, image.height - 1)
    dx = x - x0
    dy = y - y0
    top = (image.pixels[y0][x0] * (1.0 - dx)) + (image.pixels[y0][x1] * dx)
    bottom = (image.pixels[y1][x0] * (1.0 - dx)) + (image.pixels[y1][x1] * dx)
    return _clamp_to_byte((top * (1.0 - dy)) + (bottom * dy))


def _clamp_to_byte(value: float) -> int:
    return min(255, max(0, int(round(value))))
