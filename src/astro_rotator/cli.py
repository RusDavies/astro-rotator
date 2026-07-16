"""Command-line entrypoint for Astro Rotator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from astro_rotator import __version__
from astro_rotator.angle_model import (
    EquatorialGeometrySample,
    GeometrySample,
    RotationEstimate,
    geometry_rotation_estimates,
    geometry_sample_from_equatorial,
)
from astro_rotator.evidence import estimate_rotation_from_pgm
from astro_rotator.frame_catalog import FrameMetadata, read_frame_metadata
from astro_rotator.reporting import (
    AngleEvidence,
    AngleEvidenceReport,
    FrameAngleReport,
    TransformDiagnostics,
)
from astro_rotator.rotator import CanvasPolicy, InterpolationMode, rotate_pgm_file

try:
    import typer
except ImportError as exc:  # pragma: no cover - packaging/dependency guard
    raise SystemExit("The astro-rotator CLI requires the 'typer' dependency.") from exc

SUPPORTED_SUFFIXES = {".pgm", ".fit", ".fits", ".fts", ".tif", ".tiff"}
AngleSource = Literal["image-registration", "geometry"]


@dataclass(frozen=True)
class ParsedGeometrySamples:
    """Geometry samples plus evidence provenance for reporting."""

    samples: tuple[GeometrySample, ...]
    method: str
    assumptions: tuple[str, ...]


app = typer.Typer(
    help="Software field-derotation tools for altazimuth astrophotography workflows.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the package version and exit.",
    ),
) -> None:
    """Show version information when no subcommand is provided."""

    if version or ctx.invoked_subcommand is None:
        typer.echo(f"astro-rotator {__version__}")
        raise typer.Exit()


@app.command()
def derotate(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Directory containing supported input frames.",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            file_okay=False,
            dir_okay=True,
            writable=True,
            help="Directory where derotation outputs and reports will be written.",
        ),
    ],
    reference: Annotated[
        str,
        typer.Option(
            "--reference",
            "-r",
            help="Reference frame: 'first', zero-based index, filename, or path.",
        ),
    ] = "first",
    report_name: Annotated[
        str,
        typer.Option(
            "--report-name",
            help="Machine-readable evidence report filename inside the output directory.",
        ),
    ] = "angle-evidence-report.json",
    interpolation: Annotated[
        InterpolationMode,
        typer.Option(
            "--interpolation",
            help="Rotation interpolation mode for PGM outputs.",
        ),
    ] = "bilinear",
    canvas_policy: Annotated[
        CanvasPolicy,
        typer.Option(
            "--canvas",
            help="Output canvas policy. Only 'same' is currently supported.",
        ),
    ] = "same",
    fill_value: Annotated[
        int,
        typer.Option(
            "--fill-value",
            min=0,
            max=255,
            help="8-bit fill value for pixels outside the rotated source frame.",
        ),
    ] = 0,
    angle_source: Annotated[
        AngleSource,
        typer.Option(
            "--angle-source",
            help="Evidence source used for selected derotation angles.",
        ),
    ] = "image-registration",
    geometry_hour_angles: Annotated[
        str | None,
        typer.Option(
            "--geometry-hour-angles",
            help="Comma-separated frame hour angles in degrees, ordered like input frames.",
        ),
    ] = None,
    geometry_latitude: Annotated[
        float | None,
        typer.Option(
            "--geometry-latitude",
            help="Observer latitude in degrees for geometry mode.",
        ),
    ] = None,
    geometry_longitude: Annotated[
        float | None,
        typer.Option(
            "--geometry-longitude",
            help="Observer longitude in degrees, positive eastward, for timestamp geometry mode.",
        ),
    ] = None,
    geometry_timestamps: Annotated[
        str | None,
        typer.Option(
            "--geometry-timestamps",
            help=(
                "Comma-separated UTC capture timestamps, ordered like input frames. "
                "ISO 8601 with 'Z' is accepted."
            ),
        ),
    ] = None,
    geometry_right_ascension: Annotated[
        float | None,
        typer.Option(
            "--geometry-right-ascension",
            help="Target right ascension in degrees for timestamp geometry mode.",
        ),
    ] = None,
    geometry_declination: Annotated[
        float | None,
        typer.Option(
            "--geometry-declination",
            help="Target declination in degrees for geometry mode.",
        ),
    ] = None,
) -> None:
    """Estimate PGM frame rotation, write derotated outputs, and report evidence."""

    frames = discover_frames(input_dir)
    reference_frame = select_reference_frame(frames, reference)
    ensure_pgm_derotation_inputs(frames)
    geometry_samples = parse_geometry_samples(
        frames,
        angle_source=angle_source,
        geometry_hour_angles=geometry_hour_angles,
        geometry_latitude=geometry_latitude,
        geometry_longitude=geometry_longitude,
        geometry_timestamps=geometry_timestamps,
        geometry_right_ascension=geometry_right_ascension,
        geometry_declination=geometry_declination,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    report = derotate_pgm_frames(
        frames,
        reference_frame=reference_frame,
        output_dir=output_dir,
        interpolation=interpolation,
        canvas_policy=canvas_policy,
        fill_value=fill_value,
        angle_source=angle_source,
        geometry_samples=geometry_samples,
    )
    report_path = output_dir / report_name
    report_path.write_text(report.to_json(), encoding="utf-8")

    typer.echo(
        "Derotated "
        f"{len(frames)} frame(s); reference={Path(reference_frame.path).name}; "
        f"wrote outputs to {output_dir}; report={report_path}."
    )


def discover_frames(input_dir: Path) -> tuple[FrameMetadata, ...]:
    """Return supported frames in deterministic path order with metadata."""

    candidates = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not candidates:
        raise typer.BadParameter("input directory contains no supported PGM, FITS, or TIFF frames")

    frames: list[FrameMetadata] = []
    for index, path in enumerate(candidates):
        try:
            frames.append(read_frame_metadata(path, frame_index=index))
        except ValueError as exc:
            raise typer.BadParameter(f"could not read metadata for {path}: {exc}") from exc
    return tuple(frames)


def select_reference_frame(frames: tuple[FrameMetadata, ...], reference: str) -> FrameMetadata:
    """Select a reference frame by keyword, index, filename, or path."""

    if reference == "first":
        return frames[0]

    try:
        index = int(reference)
    except ValueError:
        index = None
    if index is not None:
        try:
            return frames[index]
        except IndexError as exc:
            raise typer.BadParameter(f"reference index out of range: {index}") from exc

    reference_path = Path(reference)
    for frame in frames:
        frame_path = Path(frame.path)
        if reference in {frame_path.name, str(frame_path), str(frame_path.resolve())}:
            return frame
        if reference_path == frame_path:
            return frame
    raise typer.BadParameter(f"reference frame not found: {reference}")


def ensure_pgm_derotation_inputs(frames: tuple[FrameMetadata, ...]) -> None:
    """Reject formats the first derotation engine cannot safely write yet."""

    unsupported = sorted({frame.format for frame in frames if frame.format != "pgm"})
    if unsupported:
        joined = ", ".join(unsupported)
        raise typer.BadParameter(f"derotation engine currently supports PGM only; got {joined}")


def parse_geometry_samples(
    frames: tuple[FrameMetadata, ...],
    *,
    angle_source: AngleSource,
    geometry_hour_angles: str | None,
    geometry_latitude: float | None,
    geometry_longitude: float | None,
    geometry_timestamps: str | None,
    geometry_right_ascension: float | None,
    geometry_declination: float | None,
) -> ParsedGeometrySamples | None:
    """Parse geometry samples for selected geometry mode."""

    values_supplied = (
        geometry_hour_angles is not None,
        geometry_latitude is not None,
        geometry_longitude is not None,
        geometry_timestamps is not None,
        geometry_right_ascension is not None,
        geometry_declination is not None,
    )
    if angle_source != "geometry":
        if any(values_supplied):
            raise typer.BadParameter("--geometry-* flags require --angle-source geometry")
        return None
    if geometry_latitude is None or geometry_declination is None:
        raise typer.BadParameter(
            "--angle-source geometry requires --geometry-latitude and --geometry-declination"
        )
    if geometry_hour_angles is not None:
        if (
            geometry_longitude is not None
            or geometry_timestamps is not None
            or geometry_right_ascension is not None
        ):
            raise typer.BadParameter(
                "--geometry-hour-angles cannot be combined with timestamp/location/target "
                "geometry flags"
            )
        return parse_direct_hour_angle_geometry_samples(
            frames,
            geometry_hour_angles=geometry_hour_angles,
            geometry_latitude=geometry_latitude,
            geometry_declination=geometry_declination,
        )

    return parse_timestamp_geometry_samples(
        frames,
        geometry_latitude=geometry_latitude,
        geometry_longitude=geometry_longitude,
        geometry_timestamps=geometry_timestamps,
        geometry_right_ascension=geometry_right_ascension,
        geometry_declination=geometry_declination,
    )


def parse_direct_hour_angle_geometry_samples(
    frames: tuple[FrameMetadata, ...],
    *,
    geometry_hour_angles: str,
    geometry_latitude: float,
    geometry_declination: float,
) -> ParsedGeometrySamples:
    """Parse direct-hour-angle geometry samples."""

    try:
        hour_angles = tuple(
            float(value.strip()) for value in geometry_hour_angles.split(",") if value.strip()
        )
    except ValueError as exc:
        raise typer.BadParameter("--geometry-hour-angles must contain numeric degrees") from exc
    if len(hour_angles) != len(frames):
        raise typer.BadParameter(
            "--geometry-hour-angles must include exactly one value per input frame "
            f"({len(frames)} expected, got {len(hour_angles)})"
        )
    return ParsedGeometrySamples(
        samples=tuple(
            GeometrySample(
                hour_angle_degrees=hour_angle,
                latitude_degrees=geometry_latitude,
                declination_degrees=geometry_declination,
            )
            for hour_angle in hour_angles
        ),
        method="parallactic_angle_direct_hour_angle.v1",
        assumptions=(
            "hour_angle_supplied_directly",
            "camera_parity_not_calibrated",
        ),
    )


def parse_timestamp_geometry_samples(
    frames: tuple[FrameMetadata, ...],
    *,
    geometry_latitude: float,
    geometry_longitude: float | None,
    geometry_timestamps: str | None,
    geometry_right_ascension: float | None,
    geometry_declination: float,
) -> ParsedGeometrySamples:
    """Parse timestamp/location/target geometry samples."""

    if geometry_longitude is None or geometry_right_ascension is None:
        raise typer.BadParameter(
            "timestamp geometry requires --geometry-longitude and "
            "--geometry-right-ascension when --geometry-hour-angles is omitted"
        )
    timestamps = parse_geometry_timestamps(frames, geometry_timestamps)
    return ParsedGeometrySamples(
        samples=tuple(
            geometry_sample_from_equatorial(
                EquatorialGeometrySample(
                    captured_at_utc=timestamp,
                    observer_longitude_degrees=geometry_longitude,
                    target_right_ascension_degrees=geometry_right_ascension,
                    latitude_degrees=geometry_latitude,
                    declination_degrees=geometry_declination,
                )
            )
            for timestamp in timestamps
        ),
        method="parallactic_angle_timestamp_location_target.v1",
        assumptions=(
            "hour_angle_derived_from_utc_timestamp_location_and_right_ascension",
            "longitude_positive_east",
            "compact_gmst_without_nutation",
            "camera_parity_not_calibrated",
        ),
    )


def parse_geometry_timestamps(
    frames: tuple[FrameMetadata, ...],
    geometry_timestamps: str | None,
) -> tuple[datetime, ...]:
    """Return per-frame UTC timestamps from CLI values or frame metadata."""

    if geometry_timestamps is not None:
        try:
            timestamps = tuple(
                parse_utc_datetime(value.strip())
                for value in geometry_timestamps.split(",")
                if value.strip()
            )
        except ValueError as exc:
            raise typer.BadParameter(
                "--geometry-timestamps must contain ISO 8601 UTC values"
            ) from exc
        if len(timestamps) != len(frames):
            raise typer.BadParameter(
                "--geometry-timestamps must include exactly one value per input frame "
                f"({len(frames)} expected, got {len(timestamps)})"
            )
        return timestamps

    metadata_timestamps = tuple(frame.capture.captured_at_utc for frame in frames)
    if not all(metadata_timestamps):
        raise typer.BadParameter(
            "timestamp geometry requires --geometry-timestamps because one or more frames "
            "lack capture timestamps"
        )
    return tuple(parse_utc_datetime(timestamp) for timestamp in metadata_timestamps if timestamp)


def parse_utc_datetime(value: str) -> datetime:
    """Parse an ISO 8601 timestamp and return a UTC datetime."""

    normalized = value
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def derotate_pgm_frames(
    frames: tuple[FrameMetadata, ...],
    *,
    reference_frame: FrameMetadata,
    output_dir: Path,
    interpolation: InterpolationMode,
    canvas_policy: CanvasPolicy,
    fill_value: int,
    angle_source: AngleSource,
    geometry_samples: ParsedGeometrySamples | None,
) -> AngleEvidenceReport:
    """Derotate supported PGM frames and build an evidence report."""

    geometry_estimates = geometry_evidence_estimates(
        frames,
        reference_frame=reference_frame,
        angle_source=angle_source,
        geometry_samples=geometry_samples,
    )
    return AngleEvidenceReport(
        reference_frame_path=reference_frame.path,
        coordinate_convention={
            "origin": "top_left",
            "x_positive": "right",
            "y_positive": "down",
            "positive_rotation": "counterclockwise_image_space",
        },
        assumptions=(
            "pgm_derotation_engine_v1",
            "same_size_canvas",
            f"{angle_source}_selected_for_pgm_inputs",
        ),
        frames=tuple(
            derotate_pgm_frame_report(
                frame,
                reference_frame=reference_frame,
                output_dir=output_dir,
                interpolation=interpolation,
                canvas_policy=canvas_policy,
                fill_value=fill_value,
                angle_source=angle_source,
                geometry_samples=geometry_samples,
                geometry_estimate=geometry_estimates.get(frame.path),
            )
            for frame in frames
        ),
    )


def geometry_evidence_estimates(
    frames: tuple[FrameMetadata, ...],
    *,
    reference_frame: FrameMetadata,
    angle_source: AngleSource,
    geometry_samples: ParsedGeometrySamples | None,
) -> dict[str, tuple[GeometrySample, RotationEstimate]]:
    """Return geometry estimates keyed by frame path when geometry mode is selected."""

    if angle_source != "geometry":
        return {}
    if geometry_samples is None:
        raise ValueError("geometry_samples are required for geometry mode")
    reference_index = next(
        index for index, frame in enumerate(frames) if frame.path == reference_frame.path
    )
    estimates = geometry_rotation_estimates(
        geometry_samples.samples[reference_index], geometry_samples.samples
    )
    return {
        frame.path: (sample, estimate)
        for frame, sample, estimate in zip(frames, geometry_samples.samples, estimates, strict=True)
    }


def derotate_pgm_frame_report(
    frame: FrameMetadata,
    *,
    reference_frame: FrameMetadata,
    output_dir: Path,
    interpolation: InterpolationMode,
    canvas_policy: CanvasPolicy,
    fill_value: int,
    angle_source: AngleSource,
    geometry_samples: ParsedGeometrySamples | None,
    geometry_estimate: tuple[GeometrySample, RotationEstimate] | None,
) -> FrameAngleReport:
    """Derotate one PGM frame and return its report entry."""

    if angle_source == "geometry":
        if geometry_estimate is None:
            raise ValueError("geometry estimate missing for frame")
        if geometry_samples is None:
            raise ValueError("geometry sample provenance missing for frame")
        sample, estimate = geometry_estimate
        evidence = geometry_frame_evidence(
            frame,
            reference_frame=reference_frame,
            estimate=estimate,
            sample=sample,
            method=geometry_samples.method,
            assumptions=geometry_samples.assumptions,
        )
    elif frame.path == reference_frame.path:
        evidence = reference_frame_evidence(frame, reference_frame=reference_frame)
    else:
        estimate = estimate_rotation_from_pgm(reference_frame.path, frame.path)
        evidence = estimate.to_angle_evidence(
            frame_path=frame.path,
            reference_frame_path=reference_frame.path,
        )
    derotation_degrees = evidence.derotation_degrees or 0.0
    output_path = output_dir / Path(frame.path).name
    output = rotate_pgm_file(
        frame.path,
        output_path,
        derotation_degrees,
        interpolation=interpolation,
        canvas_policy=canvas_policy,
        fill_value=fill_value,
    )
    evidence = with_derotation_output(evidence, output.__dict__)
    return FrameAngleReport(
        frame_path=frame.path,
        selected_rotation_degrees=evidence.rotation_degrees,
        selected_derotation_degrees=evidence.derotation_degrees,
        selected_source=evidence.source,
        evidence=(evidence,),
    )


def geometry_frame_evidence(
    frame: FrameMetadata,
    *,
    reference_frame: FrameMetadata,
    estimate: RotationEstimate,
    sample: GeometrySample,
    method: str,
    assumptions: tuple[str, ...],
) -> AngleEvidence:
    """Return selected geometry evidence for one frame."""

    return AngleEvidence(
        source="geometry",
        status="ok",
        frame_path=frame.path,
        reference_frame_path=reference_frame.path,
        rotation_degrees=estimate.image_rotation_degrees,
        derotation_degrees=estimate.derotation_degrees,
        method=method,
        evidence_role="selected",
        assumptions=assumptions,
        diagnostics={
            "hour_angle_degrees": sample.hour_angle_degrees,
            "latitude_degrees": sample.latitude_degrees,
            "declination_degrees": sample.declination_degrees,
            "parallactic_angle_degrees": estimate.parallactic_angle_degrees,
            "relative_field_rotation_degrees": estimate.relative_field_rotation_degrees,
            "frame_metadata": frame.to_dict(),
        },
    )


def reference_frame_evidence(
    frame: FrameMetadata,
    *,
    reference_frame: FrameMetadata,
) -> AngleEvidence:
    """Return selected zero-rotation evidence for the reference frame."""

    return AngleEvidence(
        source="image_registration",
        status="ok",
        frame_path=frame.path,
        reference_frame_path=reference_frame.path,
        rotation_degrees=0.0,
        derotation_degrees=0.0,
        method="reference_frame_identity.v1",
        evidence_role="selected",
        transform_diagnostics=TransformDiagnostics(
            transform_model="identity",
            inlier_count=0,
            rejected_match_count=0,
            rms_error_pixels=0.0,
            preprocessing={"input_format": "pgm", "stretch": "none"},
            parameters={"rotation_degrees": 0.0, "translation_pixels": [0.0, 0.0]},
        ),
        diagnostics={"frame_metadata": frame.to_dict()},
    )


def with_derotation_output(evidence: AngleEvidence, output: dict[str, object]) -> AngleEvidence:
    """Return evidence with derotation output metadata added to diagnostics."""

    return AngleEvidence(
        source=evidence.source,
        status=evidence.status,
        frame_path=evidence.frame_path,
        rotation_degrees=evidence.rotation_degrees,
        derotation_degrees=evidence.derotation_degrees,
        method=evidence.method,
        confidence=evidence.confidence,
        uncertainty_degrees=evidence.uncertainty_degrees,
        reference_frame_path=evidence.reference_frame_path,
        evidence_role=evidence.evidence_role,
        transform_diagnostics=evidence.transform_diagnostics,
        assumptions=evidence.assumptions,
        warnings=evidence.warnings,
        diagnostics={**evidence.diagnostics, "derotation_output": output},
    )


def main() -> None:
    """Run the CLI."""

    app()


if __name__ == "__main__":  # pragma: no cover
    main()
