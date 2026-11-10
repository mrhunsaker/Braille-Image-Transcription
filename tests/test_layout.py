
from braille_converter.layout import (
    LAYOUTS,
    fitted_size_px
)


def test_full_page_preserves_aspect_ratio():

    original_width = 359

    original_height = 216

    width, height = fitted_size_px(
        original_width,
        original_height,
        LAYOUTS["Full page (8 × 10.5 in)"],
        300
    )

    original_ratio = (
        original_width / original_height
    )

    output_ratio = (
        width / height
    )

    assert abs(
        original_ratio - output_ratio
    ) < 0.002

    assert width <= 2400

    assert height <= 3150


def test_half_page_dimensions():

    width, height = fitted_size_px(
        359,
        216,
        LAYOUTS["Half page (8 × 5 in)"],
        300
    )

    assert width <= 2400

    assert height <= 1500
