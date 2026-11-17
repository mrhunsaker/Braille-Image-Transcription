
"""Uploads must be validated loudly before any OCR runs."""

import io

import pytest

from PIL import Image

from braille_converter import upload_validation as validation

from braille_converter.upload_validation import (
    UploadError,
    validate_upload
)


def png_bytes(width=20, height=10):
    buffer = io.BytesIO()

    Image.new(
        "RGB",
        (width, height),
        "white"
    ).save(buffer, format="PNG")

    return buffer.getvalue()


def test_valid_upload_decodes_to_rgb():

    image = validate_upload("page.png", png_bytes())

    assert image.mode == "RGB"

    assert image.size == (20, 10)


def test_empty_upload_is_loud():

    with pytest.raises(
        UploadError,
        match="empty"
    ):
        validate_upload("page.png", b"")


def test_unsupported_suffix_is_loud():

    with pytest.raises(
        UploadError,
        match="not a supported image file"
    ):
        validate_upload("page.txt", png_bytes())


def test_non_image_bytes_are_loud():

    with pytest.raises(
        UploadError,
        match="not a recognized image"
    ):
        validate_upload(
            "page.jpg", b"this is not an image"
        )


def test_oversized_file_is_loud(monkeypatch):

    monkeypatch.setattr(
        validation,
        "max_upload_bytes",
        lambda: 10
    )

    with pytest.raises(
        UploadError,
        match="upload limit"
    ):
        validate_upload("page.png", png_bytes())


def test_oversized_dimensions_are_loud(monkeypatch):

    monkeypatch.setattr(
        validation,
        "max_image_dimension",
        lambda: 5
    )

    with pytest.raises(
        UploadError,
        match="limit is 5 px per side"
    ):
        validate_upload("page.png", png_bytes(20, 10))


def test_invalid_size_setting_is_loud(monkeypatch):

    monkeypatch.setenv(
        "BRAILLE_CONVERTER_MAX_UPLOAD_MB", "many"
    )

    with pytest.raises(
        UploadError,
        match="positive number"
    ):
        validation.max_upload_bytes()


def test_invalid_dimension_setting_is_loud(monkeypatch):

    monkeypatch.setenv(
        "BRAILLE_CONVERTER_MAX_IMAGE_DIMENSION", "0"
    )

    with pytest.raises(
        UploadError,
        match="positive number"
    ):
        validation.max_image_dimension()
