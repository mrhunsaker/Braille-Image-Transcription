
"""Tests for the OpenCV region and fraction proposals."""

from PIL import Image, ImageDraw

from braille_converter.ocr_engine import suggest_kind
from braille_converter.ocr_regions import (
    detect_fraction_bars,
    detect_fraction_parts,
    detect_text_regions,
    uncovered_candidate_regions
)


def stacked_fraction_image():
    """Return a small image containing one stacked fraction."""

    image = Image.new(
        "RGB",
        (120, 80),
        "white"
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (54, 18, 60, 36),
        fill="black"
    )

    draw.rectangle(
        (48, 38, 68, 39),
        fill="black"
    )

    draw.rectangle(
        (52, 45, 68, 63),
        fill="black"
    )

    return image


def test_detect_text_regions_does_not_merge_the_page():
    """Glyph grouping must not return one image-sized box."""

    image = stacked_fraction_image()

    regions = detect_text_regions(image)

    assert regions

    for region in regions:

        width = region[2] - region[0]

        height = region[3] - region[1]

        assert width < image.width

        assert height < image.height


def test_detect_fraction_parts_finds_bar_and_glyphs():
    """A bar needs components above and below to qualify."""

    image = stacked_fraction_image()

    parts = detect_fraction_parts(image)

    assert parts

    bar, above, below = parts[0]

    assert bar[2] - bar[0] >= 12

    assert above

    assert below

    assert detect_fraction_bars(image)


def test_uncovered_candidate_regions_skips_overlaps():
    """Candidate boxes highlight areas OCR did not cover."""

    class Record:
        def __init__(self, box):
            self.x1, self.y1, self.x2, self.y2 = box

    records = [Record((10, 10, 30, 30))]

    regions = [
        (10, 10, 30, 30),
        (80, 60, 110, 78)
    ]

    assert uncovered_candidate_regions(
        regions,
        records
    ) == [(80, 60, 110, 78)]


def test_numeric_fraction_is_literally_classified():
    """UEB fractions must not use the math table."""

    assert suggest_kind("1/4") == "literary"

    assert suggest_kind("5¼ cm") == "literary"

    assert suggest_kind("2+3") == "math"
