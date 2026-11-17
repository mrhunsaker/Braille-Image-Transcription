
"""Tests for the export artifacts and their safety rules."""

from pathlib import Path

import pytest

from braille_converter.braille_render import BrailleProfile

from braille_converter.image_pipeline import (
    ExportError,
    export_outputs
)

from braille_converter.layout import PageLayout

from braille_converter.models import OCRRecord


SAMPLE_IMAGE = (
    Path(__file__).parent
    / "test_files"
    / "67020988167474f5810b295ba0fdc993_img.jpg"
)

LAYOUT = PageLayout("half", 8.0, 5.0)


def make_record(record_id, group_id, approved=True, braille="⠁"):

    return OCRRecord(
        id=record_id,
        text="a",
        x1=0,
        y1=0,
        x2=10,
        y2=10,
        group_id=group_id,
        approved=approved,
        braille=braille
    )


def test_partial_approval_is_rejected(tmp_path):

    records = [
        make_record(1, "g1"),
        make_record(2, "g1", approved=False)
    ]

    with pytest.raises(
        ExportError,
        match="partly approved"
    ):

        export_outputs(
            SAMPLE_IMAGE,
            records,
            tmp_path,
            LAYOUT,
            BrailleProfile()
        )

    assert not list(tmp_path.glob("*_braille.*"))


def test_untranslated_group_is_rejected(tmp_path):

    with pytest.raises(
        ExportError,
        match="no Braille"
    ):

        export_outputs(
            SAMPLE_IMAGE,
            [make_record(1, "g1", braille="")],
            tmp_path,
            LAYOUT,
            BrailleProfile()
        )
