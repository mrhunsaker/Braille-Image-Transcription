
"""Tests for the export artifacts and their safety rules."""

import json
from pathlib import Path

import numpy as np
import pytest

from PIL import Image, ImageDraw

from braille_converter.braille_render import BrailleProfile

from braille_converter.image_pipeline import (
    ExportError,
    export_outputs
)

from braille_converter.layout import (
    PageLayout,
    fitted_size_px
)

from braille_converter.models import OCRRecord


SAMPLE_IMAGE = (
    Path(__file__).parent
    / "test_files"
    / "67020988167474f5810b295ba0fdc993_img.jpg"
)

LAYOUT = PageLayout("half", 8.0, 5.0)

PROFILE = BrailleProfile()


def make_record(record_id, group_id, approved=True, braille="⠁"):

    return OCRRecord(
        id=record_id,
        text="a",
        x1=20,
        y1=20,
        x2=60,
        y2=40,
        group_id=group_id,
        approved=approved,
        braille=braille
    )


def dark_pixels(image):

    return int(
        (np.asarray(image.convert("L")) < 100).sum()
    )


def make_source(tmp_path):
    """A small image with one dark box to be inpainted."""

    path = tmp_path / "source.png"

    image = Image.new(
        "RGB",
        (200, 100),
        "white"
    )

    ImageDraw.Draw(image).rectangle(
        (20, 20, 60, 40),
        fill="black"
    )

    image.save(path)

    return path


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
            PROFILE
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
            PROFILE
        )


def test_export_writes_all_four_artifacts(tmp_path):

    source = make_source(tmp_path)

    records = [make_record(1, "g1")]

    paths = export_outputs(
        source,
        records,
        tmp_path / "out",
        LAYOUT,
        PROFILE
    )

    assert [
        path.suffix for path in paths
    ] == [".png", ".pdf", ".json", ".svg"]

    assert all(
        path.exists() and path.stat().st_size > 0
        for path in paths
    )


def test_json_schema_matches_the_export(tmp_path):

    source = make_source(tmp_path)

    records = [make_record(1, "g1")]

    out = tmp_path / "out"

    paths = export_outputs(
        source,
        records,
        out,
        LAYOUT,
        PROFILE
    )

    payload = json.loads(
        paths[2].read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "1.0"

    assert payload["source_image"] == str(source)

    expected = fitted_size_px(
        200,
        100,
        LAYOUT,
        PROFILE.dpi
    )

    assert payload["original_dimensions_px"] == {
        "width": 200,
        "height": 100
    }

    assert payload["output_dimensions_px"] == {
        "width": expected[0],
        "height": expected[1]
    }

    assert "x2/y2 are exclusive" in (
        payload["coordinate_system"]
    )

    assert len(payload["notes"]) >= 4

    assert payload["records"][0]["braille"] == "⠁"


def test_png_is_scaled_and_contains_braille(tmp_path):

    source = make_source(tmp_path)

    out = tmp_path / "out"

    paths = export_outputs(
        source,
        [make_record(1, "g1")],
        out,
        LAYOUT,
        PROFILE
    )

    with Image.open(paths[0]) as result:

        assert result.size == fitted_size_px(
            200,
            100,
            LAYOUT,
            PROFILE.dpi
        )

        # PNG stores DPI as a rational number, so allow
        # the usual tiny rounding difference.
        assert tuple(
            round(value)
            for value in result.info["dpi"]
        ) == (PROFILE.dpi, PROFILE.dpi)

        dark = dark_pixels(result)

    assert dark > 0, "No Braille ink was drawn."


def test_approved_text_is_removed_before_rendering(
    tmp_path
):

    source = make_source(tmp_path)

    with Image.open(source) as opened:

        before = dark_pixels(opened)

    out = tmp_path / "out"

    paths = export_outputs(
        source,
        [make_record(1, "g1")],
        out,
        LAYOUT,
        PROFILE
    )

    with Image.open(paths[0]) as result:

        gray = result.convert("L")

        scale = result.width / 200

        region = gray.crop((
            round(20 * scale),
            round(20 * scale),
            round(60 * scale),
            round(40 * scale)
        ))

        dark_in_box = dark_pixels(region)

    assert before > 0

    # Only one Braille dot is drawn in this box; the
    # original solid black rectangle must be gone.
    assert dark_in_box < before


def test_pdf_uses_letter_page(tmp_path):

    source = make_source(tmp_path)

    paths = export_outputs(
        source,
        [make_record(1, "g1")],
        tmp_path / "out",
        LAYOUT,
        PROFILE
    )

    data = paths[1].read_bytes()

    assert data.startswith(b"%PDF")

    assert b"/MediaBox [ 0 0 612 792 ]" in data


def test_svg_contains_only_approved_braille(tmp_path):

    source = make_source(tmp_path)

    approved = make_record(1, "g1")

    excluded = make_record(2, "g2", approved=False)

    excluded.braille = "⠿"

    excluded.y1 = 60

    excluded.y2 = 80

    paths = export_outputs(
        source,
        [approved, excluded],
        tmp_path / "out",
        LAYOUT,
        PROFILE
    )

    svg = paths[3].read_text(encoding="utf-8")

    # "⠁" has one dot; "⠿" would add six more if the
    # unapproved word leaked into the tactile output.
    assert svg.count("<circle ") == 1


def test_unwritable_output_dir_is_loud(tmp_path):

    blocked = tmp_path / "not_a_directory"

    blocked.write_text("occupied", encoding="utf-8")

    with pytest.raises(OSError, match="not_a_directory"):

        export_outputs(
            SAMPLE_IMAGE,
            [make_record(1, "g1")],
            blocked,
            LAYOUT,
            PROFILE
        )
