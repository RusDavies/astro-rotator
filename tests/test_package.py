from __future__ import annotations

import astro_rotator


def test_package_exposes_version() -> None:
    assert astro_rotator.__version__ == "0.1.0"
