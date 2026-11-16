
"""Shared pytest configuration and capability checks.

Tests that need an external tool declare it with a marker:

    @pytest.mark.tesseract
    @pytest.mark.liblouis

The hook below turns those markers into skips with a clear
reason when the tool is missing, so no test can fail only
because Tesseract or Liblouis is not installed on the
machine. Tests needing both markers (for example OCR plus
translation) must declare both.
"""

from functools import lru_cache
from pathlib import Path

import pytest


@lru_cache(maxsize=1)
def tesseract_version():
    """Return the Tesseract version string, or None.

    Cached because every call spawns the binary. Expected
    OCR data is version specific (see
    tests/test_files/expected/), so tests compare this
    string with the version recorded next to the data.
    """

    try:
        import pytesseract

        from braille_converter.ocr_engine import (
            configure_tesseract
        )

        configure_tesseract()

        return str(
            pytesseract.get_tesseract_version()
        )

    except Exception:
        return None


def tesseract_installed():
    """True when pytesseract can reach a Tesseract binary."""

    return tesseract_version() is not None


def liblouis_installed():
    """True when a usable Liblouis with UEB tables exists."""

    try:
        import louis  # noqa: F401

        return True

    except ImportError:
        pass

    from braille_converter.translator import (
        find_lou_translate
    )

    return bool(find_lou_translate())


def pytest_collection_modifyitems(config, items):
    """Skip marked tests whose tool is not installed."""

    requirements = {
        "tesseract": (
            tesseract_installed(),
            "Tesseract is not installed "
            "on this machine"
        ),
        "liblouis": (
            liblouis_installed(),
            "Liblouis with UEB tables is "
            "not installed on this machine"
        )
    }

    for item in items:

        for marker, (available, reason) in (
            requirements.items()
        ):

            marked = item.get_closest_marker(
                marker
            )

            if marked and not available:

                item.add_marker(
                    pytest.mark.skip(
                        reason=reason
                    )
                )


@pytest.fixture(scope="session")
def tesseract_available():
    """Boolean for tests that branch on Tesseract."""

    return tesseract_installed()


@pytest.fixture(scope="session")
def liblouis_available():
    """Boolean for tests that branch on Liblouis."""

    return liblouis_installed()


@pytest.fixture(scope="session")
def tesseract_version_string():
    """Tesseract version recorded in expected data."""

    return tesseract_version()


@pytest.fixture(scope="session")
def ocr_records():
    """Run OCR at most once per image per session.

    The pipeline tests share one OCR result per image
    instead of re-running Tesseract for every metric.
    Returns a callable taking an image path.
    """

    from braille_converter.ocr_engine import (
        recognize_characters
    )

    cache = {}

    def records_for(image_path):

        key = str(Path(image_path).resolve())

        if key not in cache:

            cache[key] = recognize_characters(
                Path(image_path)
            )

        return cache[key]

    return records_for
