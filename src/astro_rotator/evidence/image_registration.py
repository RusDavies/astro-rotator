"""Small image-registration spike for synthetic star-field frames."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import median

from astro_rotator.angle_model import normalize_degrees
from astro_rotator.reporting.schema import AngleEvidence, EvidenceRole, TransformDiagnostics


@dataclass(frozen=True)
class StarDetection:
    """A detected star-like point in image coordinates."""

    x: float
    y: float
    brightness: float


@dataclass(frozen=True)
class ImageRegistrationEstimate:
    """Estimated transform from a reference frame to a target frame."""

    rotation_degrees: float
    translation_pixels: tuple[float, float]
    affine_translation_pixels: tuple[float, float]
    matched_stars: int
    rms_error_pixels: float
    rejected_match_count: int = 0
    residual_error_pixels: tuple[float, ...] = ()
    detected_reference_stars: int = 0
    detected_target_stars: int = 0
    max_stars: int = 40
    match_tolerance_pixels: float = 2.5

    def to_transform_diagnostics(self) -> TransformDiagnostics:
        """Return report-schema diagnostics for this registration estimate."""

        return TransformDiagnostics(
            transform_model="similarity_2d",
            inlier_count=self.matched_stars,
            rejected_match_count=self.rejected_match_count,
            rms_error_pixels=self.rms_error_pixels,
            residual_summary=_residual_summary(self.residual_error_pixels),
            preprocessing={
                "input_format": "pgm",
                "stretch": "none",
                "star_detector": "local_maxima_centroid",
                "max_stars": self.max_stars,
                "match_tolerance_pixels": self.match_tolerance_pixels,
                "detected_reference_stars": self.detected_reference_stars,
                "detected_target_stars": self.detected_target_stars,
            },
            parameters={
                "rotation_degrees": self.rotation_degrees,
                "translation_pixels": list(self.translation_pixels),
                "affine_translation_pixels": list(self.affine_translation_pixels),
            },
        )

    def to_angle_evidence(
        self,
        *,
        frame_path: str | Path,
        reference_frame_path: str | Path,
        evidence_role: EvidenceRole = "selected",
    ) -> AngleEvidence:
        """Return image-registration evidence populated with transform diagnostics."""

        derotation_degrees = normalize_degrees(-self.rotation_degrees)
        return AngleEvidence(
            source="image_registration",
            status="ok",
            frame_path=str(frame_path),
            reference_frame_path=str(reference_frame_path),
            rotation_degrees=self.rotation_degrees,
            derotation_degrees=derotation_degrees,
            method="synthetic_pairwise_star_fit.v1",
            evidence_role=evidence_role,
            transform_diagnostics=self.to_transform_diagnostics(),
            diagnostics={
                "matched_stars": self.matched_stars,
                "rejected_match_count": self.rejected_match_count,
                "rms_error_pixels": self.rms_error_pixels,
                "translation_pixels": list(self.translation_pixels),
                "affine_translation_pixels": list(self.affine_translation_pixels),
            },
        )


def estimate_rotation_from_pgm(
    reference_path: str | Path,
    target_path: str | Path,
    *,
    max_stars: int = 40,
    match_tolerance_pixels: float = 2.5,
) -> ImageRegistrationEstimate:
    """Estimate target rotation/translation relative to a reference PGM frame.

    This intentionally small spike works on the deterministic synthetic PGM
    fixtures. The production path can later swap in scikit-image/OpenCV/SEP
    backends without changing the evidence shape.
    """

    reference_image = _read_pgm(reference_path)
    target_image = _read_pgm(target_path)
    reference = _detect_stars(reference_image, max_stars=max_stars)
    target = _detect_stars(target_image, max_stars=max_stars)
    if len(reference) < 2 or len(target) < 2:
        raise ValueError("at least two detected stars are required for registration")
    pivot = (reference_image[0] / 2.0, reference_image[1] / 2.0)

    best: ImageRegistrationEstimate | None = None
    for ref_a, ref_b in combinations(reference, 2):
        ref_distance = _distance(ref_a, ref_b)
        if ref_distance < 5.0:
            continue
        ref_angle = _vector_angle_degrees(ref_a, ref_b)
        for target_a, target_b in _ordered_pairs(target):
            target_distance = _distance(target_a, target_b)
            if abs(ref_distance - target_distance) > max(2.0, ref_distance * 0.02):
                continue
            rotation = _normalize_degrees(_vector_angle_degrees(target_a, target_b) - ref_angle)
            translated_ref_a = _rotate_point(ref_a.x, ref_a.y, rotation)
            translation = (
                target_a.x - translated_ref_a[0],
                target_a.y - translated_ref_a[1],
            )
            candidate = _score_transform(
                reference=reference,
                target=target,
                rotation_degrees=rotation,
                translation=translation,
                tolerance=match_tolerance_pixels,
            )
            if _is_better(candidate, best):
                best = candidate

    if best is None:
        raise ValueError("could not fit an image-registration transform")
    pivot_translation = _pivot_translation_from_affine(
        affine_translation=best.affine_translation_pixels,
        rotation_degrees=best.rotation_degrees,
        pivot=pivot,
    )
    return ImageRegistrationEstimate(
        rotation_degrees=best.rotation_degrees,
        translation_pixels=pivot_translation,
        affine_translation_pixels=best.affine_translation_pixels,
        matched_stars=best.matched_stars,
        rms_error_pixels=best.rms_error_pixels,
        rejected_match_count=best.rejected_match_count,
        residual_error_pixels=best.residual_error_pixels,
        detected_reference_stars=best.detected_reference_stars,
        detected_target_stars=best.detected_target_stars,
        max_stars=max_stars,
        match_tolerance_pixels=match_tolerance_pixels,
    )


def _detect_stars(pgm: tuple[int, int, list[list[int]]], *, max_stars: int) -> list[StarDetection]:
    _width, _height, pixels = pgm
    flat = [value for row in pixels for value in row]
    mean = sum(flat) / len(flat)
    variance = sum((value - mean) ** 2 for value in flat) / len(flat)
    threshold = max(mean + (3.0 * math.sqrt(variance)), mean + 20.0)
    candidates: list[StarDetection] = []

    for y in range(1, len(pixels) - 1):
        for x in range(1, len(pixels[0]) - 1):
            value = pixels[y][x]
            if value < threshold:
                continue
            neighbors = [
                pixels[ny][nx]
                for ny in range(y - 1, y + 2)
                for nx in range(x - 1, x + 2)
                if nx != x or ny != y
            ]
            if value < max(neighbors):
                continue
            candidates.append(_centroid(pixels, x, y, background=mean))

    candidates.sort(key=lambda star: star.brightness, reverse=True)
    selected: list[StarDetection] = []
    for candidate in candidates:
        if all(_distance(candidate, star) >= 3.0 for star in selected):
            selected.append(candidate)
        if len(selected) >= max_stars:
            break
    return selected


def _centroid(
    pixels: list[list[int]],
    center_x: int,
    center_y: int,
    *,
    background: float,
) -> StarDetection:
    weighted_x = 0.0
    weighted_y = 0.0
    total = 0.0
    height = len(pixels)
    width = len(pixels[0])
    for y in range(max(0, center_y - 2), min(height, center_y + 3)):
        for x in range(max(0, center_x - 2), min(width, center_x + 3)):
            weight = max(0.0, pixels[y][x] - background)
            weighted_x += x * weight
            weighted_y += y * weight
            total += weight
    if total == 0.0:
        return StarDetection(x=float(center_x), y=float(center_y), brightness=0.0)
    return StarDetection(x=weighted_x / total, y=weighted_y / total, brightness=total)


def _score_transform(
    *,
    reference: list[StarDetection],
    target: list[StarDetection],
    rotation_degrees: float,
    translation: tuple[float, float],
    tolerance: float,
) -> ImageRegistrationEstimate:
    unmatched = set(range(len(target)))
    residuals: list[float] = []

    for ref_star in reference:
        x, y = _rotate_point(ref_star.x, ref_star.y, rotation_degrees)
        x += translation[0]
        y += translation[1]
        nearest_index: int | None = None
        nearest_error = math.inf
        for index in unmatched:
            candidate = target[index]
            error = math.hypot(candidate.x - x, candidate.y - y)
            if error < nearest_error:
                nearest_index = index
                nearest_error = error
        if nearest_index is not None and nearest_error <= tolerance:
            unmatched.remove(nearest_index)
            residuals.append(nearest_error)

    matched = len(residuals)
    rms = math.sqrt(sum(error * error for error in residuals) / matched) if matched else math.inf
    return ImageRegistrationEstimate(
        rotation_degrees=rotation_degrees,
        translation_pixels=translation,
        affine_translation_pixels=translation,
        matched_stars=matched,
        rms_error_pixels=rms,
        rejected_match_count=max(0, min(len(reference), len(target)) - matched),
        residual_error_pixels=tuple(residuals),
        detected_reference_stars=len(reference),
        detected_target_stars=len(target),
        match_tolerance_pixels=tolerance,
    )


def _is_better(
    candidate: ImageRegistrationEstimate,
    best: ImageRegistrationEstimate | None,
) -> bool:
    if best is None:
        return True
    if candidate.matched_stars != best.matched_stars:
        return candidate.matched_stars > best.matched_stars
    return candidate.rms_error_pixels < best.rms_error_pixels


def _read_pgm(path: str | Path) -> tuple[int, int, list[list[int]]]:
    data = Path(path).read_bytes()
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

    if tokens[0] != b"P5":
        raise ValueError("only binary PGM/P5 images are supported")
    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    if max_value != 255:
        raise ValueError("only 8-bit PGM images are supported")
    if index < len(data) and data[index] in b" \t\r\n":
        index += 1
    expected = width * height
    body = data[index : index + expected]
    if len(body) != expected:
        raise ValueError("PGM image body has unexpected length")
    rows = [list(body[row * width : (row + 1) * width]) for row in range(height)]
    return width, height, rows


def _ordered_pairs(stars: list[StarDetection]):
    for first, second in combinations(stars, 2):
        yield first, second
        yield second, first


def _distance(first: StarDetection, second: StarDetection) -> float:
    return math.hypot(second.x - first.x, second.y - first.y)


def _vector_angle_degrees(first: StarDetection, second: StarDetection) -> float:
    return math.degrees(math.atan2(-(second.y - first.y), second.x - first.x))


def _rotate_point(x: float, y: float, angle_degrees: float) -> tuple[float, float]:
    theta = math.radians(angle_degrees)
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)
    return (cos_theta * x) + (sin_theta * y), (-sin_theta * x) + (cos_theta * y)


def _pivot_translation_from_affine(
    *,
    affine_translation: tuple[float, float],
    rotation_degrees: float,
    pivot: tuple[float, float],
) -> tuple[float, float]:
    rotated_pivot = _rotate_point(pivot[0], pivot[1], rotation_degrees)
    pivot_offset = (pivot[0] - rotated_pivot[0], pivot[1] - rotated_pivot[1])
    return (
        affine_translation[0] - pivot_offset[0],
        affine_translation[1] - pivot_offset[1],
    )


def _normalize_degrees(value: float) -> float:
    normalized = (value + 180.0) % 360.0 - 180.0
    if normalized == -180.0 and value > 0:
        return 180.0
    return normalized


def _residual_summary(residuals: tuple[float, ...]) -> dict[str, float]:
    if not residuals:
        return {}
    return {
        "count": float(len(residuals)),
        "mean_pixels": sum(residuals) / len(residuals),
        "median_pixels": median(residuals),
        "max_pixels": max(residuals),
    }
