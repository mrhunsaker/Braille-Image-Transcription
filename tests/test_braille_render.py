
import pytest

from braille_converter.braille_render import (
    braille_cells,
    layout_braille_groups,
    mm_to_px,
    write_tactile_svg,
    BrailleProfile
)

from braille_converter.models import OCRRecord


def make_record(record_id, group_id, x1, y1, braille="⠁⠃"):
    """Build a record with a known source position."""

    return OCRRecord(
        id=record_id,
        text="a",
        x1=x1,
        y1=y1,
        x2=x1 + 20,
        y2=y1 + 10,
        group_id=group_id,
        braille=braille
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


def test_same_line_words_are_spaced_apart():
    """Overlapping source boxes must not produce overlapping dots."""

    profile = BrailleProfile()

    groups = [
        [make_record(1, "g1", 20, 10)],
        [make_record(2, "g2", 25, 10)]
    ]

    placements = layout_braille_groups(
        groups,
        profile,
        (100, 50),
        (1000, 500)
    )

    assert len(placements) == 2

    first, second = placements

    assert first.x == 200

    assert first.y == second.y == 100

    assert second.x >= (
        first.x + first.width + mm_to_px(
            profile.cell_pitch_mm,
            profile.dpi
        )
    )

    assert second.x > 250


def test_overflow_wraps_and_pushes_later_source_lines():
    """A wrapped word must not collide with the next source line."""

    profile = BrailleProfile()

    word = "⠁⠃⠁⠃⠁⠃"

    groups = [
        [make_record(1, "g1", 8, 10, word)],
        [make_record(2, "g2", 12, 10, word)],
        [make_record(3, "g3", 16, 10, word)],
        [make_record(4, "g4", 10, 30, word)]
    ]

    placements = layout_braille_groups(
        groups,
        profile,
        (100, 50),
        (1000, 600)
    )

    assert [placement.row for placement in placements] == [
        0,
        1,
        2,
        3
    ]

    assert placements[1].x == mm_to_px(
        profile.cell_pitch_mm,
        profile.dpi
    )

    assert placements[2].y > (
        placements[1].y + placements[1].height
    )

    assert placements[3].y > (
        placements[2].y + placements[2].height
    )


def test_page_overflow_compacts_rows_without_overlap():

    profile = BrailleProfile()

    groups = [
        [make_record(index + 1, f"g{index + 1}", 10, y)]
        for index, y in enumerate(
            (5, 15, 25, 35, 45, 55)
        )
    ]

    placements = layout_braille_groups(
        groups,
        profile,
        (100, 60),
        (1000, 600)
    )

    assert len(placements) == 6

    assert max(
        placement.y + placement.height
        for placement in placements
    ) <= 600

    for index, first in enumerate(placements):

        for second in placements[index + 1:]:

            assert not (
                first.x < second.x + second.width
                and second.x < first.x + first.width
                and first.y < second.y + second.height
                and second.y < first.y + first.height
            )


def test_word_too_wide_for_page_is_split_across_rows():

    profile = BrailleProfile()

    placements = layout_braille_groups(
        [[make_record(1, "g1", 10, 10, "⠁" * 30)]],
        profile,
        (100, 50),
        (1000, 500)
    )

    assert len(placements) == 3

    assert [placement.row for placement in placements] == [
        0,
        1,
        2
    ]

    assert "".join(
        placement.braille
        for placement in placements
    ) == "⠁" * 30

    margin = mm_to_px(
        profile.cell_pitch_mm,
        profile.dpi
    )

    assert placements[0].x >= margin

    assert all(
        placement.x == margin
        for placement in placements[1:]
    )


def test_group_without_drawable_cells_is_loud():

    with pytest.raises(ValueError, match="no drawable cells"):

        layout_braille_groups(
            [[make_record(1, "g1", 10, 10, "  ")]],
            BrailleProfile(),
            (100, 50),
            (1000, 500)
        )


def test_svg_uses_the_shared_placements(tmp_path):

    profile = BrailleProfile()

    groups = [
        [make_record(1, "g1", 20, 10)],
        [make_record(2, "g2", 25, 10)]
    ]

    placements = layout_braille_groups(
        groups,
        profile,
        (100, 50),
        (1000, 500)
    )

    path = tmp_path / "tactile.svg"

    write_tactile_svg(
        path,
        placements,
        profile,
        (1000, 500)
    )

    svg = path.read_text(encoding="utf-8")

    mm_per_pixel = 25.4 / profile.dpi

    radius = profile.dot_diameter_mm / 2

    for placement in placements:

        cx = placement.x * mm_per_pixel + radius

        cy = placement.y * mm_per_pixel + radius

        assert f'cx="{cx:.3f}"' in svg

        assert f'cy="{cy:.3f}"' in svg

    # ⠁ has one dot and ⠃ has two, for each of two words.
    assert svg.count("<circle ") == 6
