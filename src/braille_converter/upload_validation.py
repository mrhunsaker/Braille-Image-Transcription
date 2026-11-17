
"""Validation for uploaded worksheet images.

Every rejected upload raises UploadError with an actionable
message. The GUI shows that message in its modal dialog, so
an invalid file is never silently ignored.
"""

import io
import os
from pathlib import Path

from PIL import Image, UnidentifiedImageError


ALLOWED_SUFFIXES = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp"
}

DEFAULT_MAX_SIZE_MB = 25.0
DEFAULT_MAX_DIMENSION = 8000


class UploadError(ValueError):
    """An upload was rejected; the message is user-facing."""


def _positive_number(name, raw, default):
    """Parse a positive numeric environment setting."""

    raw = str(raw).strip()

    if not raw:
        return default

    try:
        value = float(raw)

    except ValueError as exc:
        raise UploadError(
            f"Invalid {name}={raw!r}: expected a "
            "positive number."
        ) from exc

    if value <= 0:
        raise UploadError(
            f"Invalid {name}={raw!r}: expected a "
            "positive number."
        )

    return value


def max_upload_bytes():
    """Return the configured file-size limit in bytes."""

    raw = os.environ.get(
        "BRAILLE_CONVERTER_MAX_UPLOAD_MB", ""
    )

    return int(
        _positive_number(
            "BRAILLE_CONVERTER_MAX_UPLOAD_MB",
            raw,
            DEFAULT_MAX_SIZE_MB
        )
        * 1024 * 1024
    )


def max_image_dimension():
    """Return the configured pixel-dimension limit."""

    raw = os.environ.get(
        "BRAILLE_CONVERTER_MAX_IMAGE_DIMENSION", ""
    )

    return int(
        _positive_number(
            "BRAILLE_CONVERTER_MAX_IMAGE_DIMENSION",
            raw,
            DEFAULT_MAX_DIMENSION
        )
    )


def validate_upload(name, data):
    """Decode and validate an upload, returning an RGB Image.

    The returned image is detached from the input buffer, so
    it stays usable after the caller closes its resources.
    """

    name = Path(name).name

    suffix = Path(name).suffix.lower()

    if suffix not in ALLOWED_SUFFIXES:
        raise UploadError(
            f"'{name}' is not a supported image file. "
            "Choose a "
            + ", ".join(sorted(ALLOWED_SUFFIXES))
            + " file."
        )

    if not data:
        raise UploadError(
            f"'{name}' is empty. Choose a different file."
        )

    limit = max_upload_bytes()

    if len(data) > limit:
        raise UploadError(
            f"'{name}' is {len(data) / (1024 * 1024):.1f} "
            f"MB, which exceeds the "
            f"{limit / (1024 * 1024):g} MB upload limit. "
            "Resize or compress the image and try again. "
            "Raise BRAILLE_CONVERTER_MAX_UPLOAD_MB if "
            "the larger file is intentional."
        )

    try:
        with Image.open(io.BytesIO(data)) as opened:

            width, height = opened.size

            maximum = max_image_dimension()

            if width > maximum or height > maximum:

                raise UploadError(
                    f"'{name}' is {width} × {height} px; "
                    f"the limit is {maximum} px per side. "
                    "Resize the image and try again. "
                    "Raise "
                    "BRAILLE_CONVERTER_MAX_IMAGE_DIMENSION "
                    "if the larger image is intentional."
                )

            # Force a full decode so truncated or corrupt
            # files fail here instead of during OCR.
            opened.load()

            return opened.convert("RGB")

    except UploadError:
        raise

    except UnidentifiedImageError as exc:
        raise UploadError(
            f"'{name}' is not a recognized image. "
            "Choose a valid "
            + ", ".join(sorted(ALLOWED_SUFFIXES))
            + " file."
        ) from exc

    except Image.DecompressionBombError as exc:
        raise UploadError(
            f"'{name}' is too large to decode safely: "
            f"{exc}. Resize the image and try again."
        ) from exc

    except Exception as exc:
        raise UploadError(
            f"Could not decode '{name}': {exc}"
        ) from exc
