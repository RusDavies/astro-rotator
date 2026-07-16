"""Frame discovery, ordering, and metadata cataloging."""

from astro_rotator.frame_catalog.metadata import (
    AstrometryMetadata,
    CaptureMetadata,
    FrameGeometry,
    FrameMetadata,
    SupportedImageFormat,
)
from astro_rotator.frame_catalog.readers import (
    read_fits_metadata,
    read_frame_metadata,
    read_pgm_metadata,
    read_tiff_metadata,
)

__all__ = [
    "AstrometryMetadata",
    "CaptureMetadata",
    "FrameGeometry",
    "FrameMetadata",
    "SupportedImageFormat",
    "read_fits_metadata",
    "read_frame_metadata",
    "read_pgm_metadata",
    "read_tiff_metadata",
]
