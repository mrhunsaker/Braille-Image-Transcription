
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageDraw


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
    records,
    profile,
    source_size,
    output_size
):

    """
    Creates a physical-size SVG with Braille dots.

    Coordinates are mapped from the original image
    into the enlarged output image.

    This is a vector dot representation, not a
    universal embosser file format.
    """

    source_width, source_height = source_size

    output_width, output_height = output_size

    page_width_mm = (
        output_width / profile.dpi * 25.4
    )

    page_height_mm = (
        output_height / profile.dpi * 25.4
    )

    scale_x = output_width / source_width

    scale_y = output_height / source_height

    mm_per_pixel = 25.4 / profile.dpi

    horizontal_pitch = profile.horizontal_dot_pitch_mm

    vertical_pitch = profile.vertical_dot_pitch_mm

    diameter = profile.dot_diameter_mm

    circles = []

    # Group the records so the entire word is rendered
    # at the first character's position.
    groups = {}

    for record in records:

        if record.group_id not in groups:

            groups[record.group_id] = []

        groups[record.group_id].append(record)

    for group in groups.values():

        group.sort(key=lambda r: r.x1)

        braille = next(
            (r.braille for r in group if r.braille),
            ""
        )

        if not braille:
            continue

        x = min(r.x1 for r in group)

        y = min(r.y1 for r in group)

        x_mm = x * scale_x * mm_per_pixel

        y_mm = y * scale_y * mm_per_pixel

        for column, mask in enumerate(
            braille_cells(braille)
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
