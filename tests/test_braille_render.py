
from braille_converter.braille_render import (
    braille_cells,
    mm_to_px,
    BrailleProfile
)


def test_unicode_braille_cell_extraction():

    result = list(
        braille_cells("⠁⠃")
    )

    assert result == [1, 3]


def test_braille_dot_size():

    profile = BrailleProfile()

    pixels = mm_to_px(
        profile.dot_diameter_mm,
        profile.dpi
    )

    assert pixels == 18


def test_braille_profile():

    profile = BrailleProfile()

    assert profile.dot_diameter_mm == 1.5

    assert profile.cell_pitch_mm == 6.2

    assert profile.line_pitch_mm == 10.2
