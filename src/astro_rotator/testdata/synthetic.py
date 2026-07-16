"""Deterministic synthetic star-field stack generation."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SCHEMA = "astro-rotator.synthetic-stack.v1"


@dataclass(frozen=True)
class SyntheticStackConfig:
    """Configuration for a deterministic synthetic star-field stack."""

    name: str = "pure_rotation_seed_42"
    seed: int = 42
    width: int = 128
    height: int = 128
    star_count: int = 80
    background_level: float = 12.0
    noise_sigma: float = 1.5
    psf_sigma: float = 1.2
    angle_degrees: tuple[float, ...] = (0.0, 0.5, 1.0)
    translation_pixels: tuple[tuple[float, float], ...] | None = None
    missing_star_fraction: float = 0.0
    hot_pixel_count: int = 0
    output_format: Literal["pgm"] = "pgm"
    pivot_pixels: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.star_count <= 0:
            raise ValueError("star_count must be positive")
        if not self.angle_degrees:
            raise ValueError("angle_degrees must contain at least one frame")
        if self.psf_sigma <= 0:
            raise ValueError("psf_sigma must be positive")
        if not 0.0 <= self.missing_star_fraction <= 1.0:
            raise ValueError("missing_star_fraction must be between 0 and 1")
        if self.hot_pixel_count < 0:
            raise ValueError("hot_pixel_count must not be negative")
        if self.translation_pixels is not None and len(self.translation_pixels) != len(
            self.angle_degrees
        ):
            raise ValueError("translation_pixels must match angle_degrees length")


@dataclass(frozen=True)
class Star:
    """Base star model before per-frame transforms."""

    x: float
    y: float
    flux: float


def generate_synthetic_stack(
    output_dir: str | Path,
    config: SyntheticStackConfig | None = None,
) -> dict[str, Any]:
    """Generate a deterministic synthetic stack and return its manifest."""

    config = config or SyntheticStackConfig()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stars = _make_base_stars(config)
    pivot = config.pivot_pixels or (config.width / 2.0, config.height / 2.0)
    translations = config.translation_pixels or tuple((0.0, 0.0) for _ in config.angle_degrees)

    frames: list[dict[str, Any]] = []
    for index, (angle, translation) in enumerate(
        zip(config.angle_degrees, translations, strict=True)
    ):
        filename = f"frame_{index:03d}.{config.output_format}"
        frame_path = output_path / filename
        frame_rng = random.Random(config.seed + 10_000 + index)
        image = _render_frame(
            config=config,
            stars=stars,
            angle_degrees=angle,
            translation=translation,
            pivot=pivot,
            rng=frame_rng,
        )
        _write_pgm(frame_path, image)
        frames.append(
            {
                "path": filename,
                "angle_degrees_from_reference": angle,
                "translation_pixels_from_reference": list(translation),
                "pivot_pixels": list(pivot),
            }
        )

    manifest = _manifest(config=config, frames=frames)
    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _make_base_stars(config: SyntheticStackConfig) -> list[Star]:
    rng = random.Random(config.seed)
    margin = max(4.0, config.psf_sigma * 4.0)
    stars: list[Star] = []
    for _ in range(config.star_count):
        x = rng.uniform(margin, config.width - margin)
        y = rng.uniform(margin, config.height - margin)
        flux = rng.uniform(90.0, 230.0)
        stars.append(Star(x=x, y=y, flux=flux))
    return stars


def _render_frame(
    *,
    config: SyntheticStackConfig,
    stars: list[Star],
    angle_degrees: float,
    translation: tuple[float, float],
    pivot: tuple[float, float],
    rng: random.Random,
) -> list[list[int]]:
    image = [
        [config.background_level + rng.gauss(0.0, config.noise_sigma) for _ in range(config.width)]
        for _ in range(config.height)
    ]
    for star in stars:
        if config.missing_star_fraction and rng.random() < config.missing_star_fraction:
            continue
        x, y = _transform_point(star.x, star.y, angle_degrees, translation, pivot)
        _add_gaussian_star(image, x, y, star.flux, config.psf_sigma)

    for _ in range(config.hot_pixel_count):
        x = rng.randrange(config.width)
        y = rng.randrange(config.height)
        image[y][x] += rng.uniform(180.0, 255.0)

    return [[_clamp_to_byte(value) for value in row] for row in image]


def _transform_point(
    x: float,
    y: float,
    angle_degrees: float,
    translation: tuple[float, float],
    pivot: tuple[float, float],
) -> tuple[float, float]:
    theta = math.radians(angle_degrees)
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)
    dx = x - pivot[0]
    dy = y - pivot[1]

    # Positive rotation is counterclockwise in displayed image coordinates,
    # where y increases downward.
    rotated_x = pivot[0] + (cos_theta * dx) + (sin_theta * dy)
    rotated_y = pivot[1] - (sin_theta * dx) + (cos_theta * dy)
    return rotated_x + translation[0], rotated_y + translation[1]


def _add_gaussian_star(
    image: list[list[float]],
    x: float,
    y: float,
    flux: float,
    sigma: float,
) -> None:
    radius = max(1, math.ceil(3.0 * sigma))
    center_x = round(x)
    center_y = round(y)
    height = len(image)
    width = len(image[0])
    for py in range(center_y - radius, center_y + radius + 1):
        if py < 0 or py >= height:
            continue
        for px in range(center_x - radius, center_x + radius + 1):
            if px < 0 or px >= width:
                continue
            distance_squared = ((px - x) ** 2) + ((py - y) ** 2)
            image[py][px] += flux * math.exp(-distance_squared / (2.0 * sigma * sigma))


def _write_pgm(path: Path, pixels: list[list[int]]) -> None:
    width = len(pixels[0])
    height = len(pixels)
    header = f"P5\n{width} {height}\n255\n".encode("ascii")
    body = bytes(value for row in pixels for value in row)
    path.write_bytes(header + body)


def _manifest(config: SyntheticStackConfig, frames: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "name": config.name,
        "generator": {
            "seed": config.seed,
            "width": config.width,
            "height": config.height,
            "star_count": config.star_count,
            "background_level": config.background_level,
            "noise_sigma": config.noise_sigma,
            "psf_sigma": config.psf_sigma,
            "missing_star_fraction": config.missing_star_fraction,
            "hot_pixel_count": config.hot_pixel_count,
            "output_format": config.output_format,
        },
        "coordinate_convention": {
            "origin": "top_left",
            "x_positive": "right",
            "y_positive": "down",
            "angle_unit": "degrees",
            "positive_rotation": "counterclockwise_image_space",
        },
        "reference_frame": frames[0]["path"],
        "frames": frames,
    }


def _clamp_to_byte(value: float) -> int:
    return min(255, max(0, int(round(value))))
