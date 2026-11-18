
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any



@dataclass
class BrailleProfile:

    # Physical dimensions in millimetres.

    dot_diameter_mm: float = 1.5

    horizontal_dot_pitch_mm: float = 2.3

    vertical_dot_pitch_mm: float = 2.5

    cell_pitch_mm: float = 6.2

    line_pitch_mm: float = 10.2

    dpi: int = 300


# Unicode Braille dot positions.
#
# Bit 0 = dot 1
# Bit 1 = dot 2
# Bit 2 = dot 3
# Bit 3 = dot 4
# Bit 4 = dot 5
# Bit 5 = dot 6

DOT_POSITIONS = {

    0: (0, 0),

    1: (0, 1),

    2: (0, 2),

    3: (1, 0),

    4: (1, 1),

    5: (1, 2)

}


def braille_cells(text):

    for char in text:

        code = ord(char)

        if 0x2800 <= code <= 0x28FF:

            yield code - 0x2800


def mm_to_px(mm, dpi):

    return max(
        1,
        round(mm * dpi / 25.4)
    )


@dataclass(frozen=True)
class BraillePlacement:
    """One rendered word at a collision-free page position."""

    group: list[Any]

    braille: str

    x: int

    y: int

    width: int

    height: int

    row: int


def braille_cell_characters(text):
    """Return the individual Unicode Braille cells in ``text``."""

    return [
        char
        for char in text
        if 0x2800 <= ord(char) <= 0x28FF
    ]


def braille_cell_count(text):
    """Return the number of physical Braille cells in ``text``."""

    return len(braille_cell_characters(text))


def layout_braille_groups(
    groups,
    profile,
    source_size,
    output_size
):
    """Place word groups on the output page without overlap.

    Each word starts near the scaled position of its source box.
    Words on a source line are spaced at least one empty cell apart.
    A word that would run past the right margin wraps to a new row;
    later source lines are pushed down when a wrap needs the space.

    The same placements are used by the PNG/PDF renderer and the
    tactile SVG, so the two artifacts cannot drift apart.
    """

    source_width, source_height = source_size

    output_width, output_height = output_size

    if source_width <= 0 or source_height <= 0:
        raise ValueError("Source image has no drawable area.")

    if output_width <= 0 or output_height <= 0:
        raise ValueError("Output page has no drawable area.")

    scale_x = output_width / source_width

    scale_y = output_height / source_height

    cell_pitch = mm_to_px(
        profile.cell_pitch_mm,
        profile.dpi
    )

    vertical_pitch = mm_to_px(
        profile.vertical_dot_pitch_mm,
        profile.dpi
    )

    diameter = mm_to_px(
        profile.dot_diameter_mm,
        profile.dpi
    )

    line_pitch = mm_to_px(
        profile.line_pitch_mm,
        profile.dpi
    )

    # Three dot rows plus the dot diameter. ``cell_pitch`` is
    # deliberately larger than the ink width, leaving one blank
    # cell between neighbouring words.
    word_height = 2 * vertical_pitch + diameter

    gap_x = cell_pitch

    gap_y = max(1, line_pitch - word_height)

    left_margin = cell_pitch

    right_limit = output_width - left_margin

    usable_width = right_limit - left_margin

    max_cells = usable_width // cell_pitch

    if max_cells < 1:
        raise ValueError(
            "The page is too narrow for one Braille cell. "
            "Choose a larger page layout."
        )

    # Source lines whose top edges are closer than one word
    # height are treated as one line; that tolerates different
    # glyph heights without merging adjacent physical lines.
    source_line_tolerance = word_height

    candidates = []

    for group in groups:

        ordered = sorted(
            group,
            key=lambda record: record.x1
        )

        braille = next(
            (
                record.braille
                for record in ordered
                if record.braille
            ),
            ""
        )

        if not braille:
            continue

        cell_characters = braille_cell_characters(
            braille
        )

        if not cell_characters:

            group_id = getattr(
                ordered[0],
                "group_id",
                "unknown"
            )

            raise ValueError(
                f"Braille for group {group_id!r} "
                "contains no drawable cells."
            )

        # A long translated token is continued on the next row
        # instead of being clipped at the page edge.
        chunks = [
            "".join(
                cell_characters[
                    start:start + max_cells
                ]
            )
            for start in range(
                0,
                len(cell_characters),
                max_cells
            )
        ]

        chunk_widths = [
            braille_cell_count(chunk) * cell_pitch
            for chunk in chunks
        ]

        candidates.append(
            {
                "group": ordered,
                "chunks": chunks,
                "chunk_widths": chunk_widths,
                "desired_x": round(
                    min(r.x1 for r in ordered) * scale_x
                ),
                "desired_y": round(
                    min(r.y1 for r in ordered) * scale_y
                )
            }
        )

    candidates.sort(
        key=lambda item: (
            item["desired_y"],
            item["desired_x"]
        )
    )

    source_lines = []

    for candidate in candidates:

        for line in source_lines:

            if (
                abs(
                    candidate["desired_y"]
                    - line["source_y"]
                )
                <= source_line_tolerance
            ):
                line["items"].append(candidate)

                line["source_y"] = min(
                    line["source_y"],
                    candidate["desired_y"]
                )

                break

        else:

            source_lines.append(
                {
                    "source_y": candidate["desired_y"],
                    "items": [candidate]
                }
            )

    placements = []

    layout_details = []

    previous_bottom = None

    row_index = -1

    needs_compaction = False

    for line in source_lines:

        items = sorted(
            line["items"],
            key=lambda item: item["desired_x"]
        )

        line_top = min(
            item["desired_y"]
            for item in items
        )

        row_index += 1

        row_y = max(line_top, left_margin)

        if previous_bottom is not None:

            row_y = max(
                row_y,
                previous_bottom + gap_y
            )

        cursor_x = left_margin

        row_bottom = row_y + word_height

        for item in items:

            offset = item["desired_y"] - line_top

            x = max(
                item["desired_x"],
                cursor_x,
                left_margin
            )

            if x + item["chunk_widths"][0] > right_limit:

                # Reflow from the left of a fresh row.
                row_y = row_bottom + gap_y

                row_bottom = row_y + word_height

                x = left_margin

                row_index += 1

            for chunk_index, chunk in enumerate(
                item["chunks"]
            ):

                if chunk_index:

                    # A continued word always starts a new
                    # row at the left margin.
                    row_y = row_bottom + gap_y

                    row_bottom = row_y + word_height

                    x = left_margin

                    row_index += 1

                chunk_y = row_y + offset

                chunk_width = item[
                    "chunk_widths"
                ][chunk_index]

                row_bottom = max(
                    row_bottom,
                    chunk_y + word_height
                )

                if chunk_y + word_height > output_height:

                    needs_compaction = True

                placements.append(
                    BraillePlacement(
                        group=item["group"],
                        braille=chunk,
                        x=x,
                        y=chunk_y,
                        width=chunk_width,
                        height=word_height,
                        row=row_index
                    )
                )

                layout_details.append(
                    {
                        "index": len(placements) - 1,
                        "row": row_index,
                        "offset": offset
                    }
                )

            cursor_x = x + chunk_width + gap_x

        previous_bottom = row_bottom

    if needs_compaction:

        # A wrap used space needed by a later source line. Pack
        # the rows from the top, preserving row order and each
        # word's small vertical offset within its source line.
        rows = sorted(
            {detail["row"] for detail in layout_details}
        )

        # Use the normal line gap when it fits. If reflowing
        # produced more rows than the page allows at that
        # pitch, tighten only the gap; word boxes still never
        # overlap.
        row_span = (
            max(
                detail["offset"]
                for detail in layout_details
            )
            + word_height
        )

        available_gap = (
            output_height
            - left_margin
            - len(rows) * row_span
        )

        compact_gap = min(
            gap_y,
            max(
                0,
                available_gap
                // max(1, len(rows) - 1)
            )
        )

        row_bases = {}

        compact_y = left_margin

        for row in rows:

            row_bases[row] = compact_y

            max_offset = max(
                detail["offset"]
                for detail in layout_details
                if detail["row"] == row
            )

            compact_y += (
                max_offset + word_height + compact_gap
            )

        for detail in layout_details:

            new_y = (
                row_bases[detail["row"]]
                + detail["offset"]
            )

            if new_y + word_height > output_height:

                raise ValueError(
                    "Braille layout still exceeds the page "
                    "after reflowing. Choose the full-page "
                    "layout or fewer source lines."
                )

            index = detail["index"]

            placements[index] = replace(
                placements[index],
                y=new_y
            )

    return placements


def draw_braille(
    draw,
    x,
    y,
    text,
    profile,
    fill=(0, 0, 0)
):

    diameter = mm_to_px(
        profile.dot_diameter_mm,
        profile.dpi
    )

    horizontal_pitch = mm_to_px(
        profile.horizontal_dot_pitch_mm,
        profile.dpi
    )

    vertical_pitch = mm_to_px(
        profile.vertical_dot_pitch_mm,
        profile.dpi
    )

    cell_pitch = mm_to_px(
        profile.cell_pitch_mm,
        profile.dpi
    )

    for column, mask in enumerate(
        braille_cells(text)
    ):

        for dot, (dx, dy) in DOT_POSITIONS.items():

            if mask & (1 << dot):

                cx = (
                    x
                    + column * cell_pitch
                    + dx * horizontal_pitch
                )

                cy = (
                    y
                    + dy * vertical_pitch
                )

                draw.ellipse(
                    (
                        cx,
                        cy,
                        cx + diameter,
                        cy + diameter
                    ),
                    fill=fill
                )


def write_tactile_svg(
    path,
    placements,
    profile,
    output_size
):

    """
    Create a physical-size SVG from shared Braille placements.

    ``placements`` comes from :func:`layout_braille_groups`, so
    tactile dots land in the same conflict-free positions as the
    PNG and PDF overlays. This is a vector dot representation,
    not a universal embosser file format.
    """

    output_width, output_height = output_size

    page_width_mm = (
        output_width / profile.dpi * 25.4
    )

    page_height_mm = (
        output_height / profile.dpi * 25.4
    )

    mm_per_pixel = 25.4 / profile.dpi

    horizontal_pitch = profile.horizontal_dot_pitch_mm

    vertical_pitch = profile.vertical_dot_pitch_mm

    diameter = profile.dot_diameter_mm

    circles = []

    for placement in placements:

        x_mm = placement.x * mm_per_pixel

        y_mm = placement.y * mm_per_pixel

        for column, mask in enumerate(
            braille_cells(placement.braille)
        ):

            for dot, (dx, dy) in DOT_POSITIONS.items():

                if mask & (1 << dot):

                    cx = (
                        x_mm
                        + column * profile.cell_pitch_mm
                        + dx * horizontal_pitch
                        + diameter / 2
                    )

                    cy = (
                        y_mm
                        + dy * vertical_pitch
                        + diameter / 2
                    )

                    radius = diameter / 2

                    circles.append(
                        f'<circle cx="{cx:.3f}" '
                        f'cy="{cy:.3f}" '
                        f'r="{radius:.3f}" '
                        f'fill="black"/>'
                    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{page_width_mm:.2f}mm" '
        f'height="{page_height_mm:.2f}mm" '
        f'viewBox="0 0 {page_width_mm:.2f} '
        f'{page_height_mm:.2f}">'
        + "".join(circles)
        + "</svg>"
    )

    Path(path).write_text(
        svg,
        encoding="utf-8"
    )
