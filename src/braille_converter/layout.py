
from dataclasses import dataclass


@dataclass
class PageLayout:

    name: str

    content_width_in: float

    content_height_in: float


LAYOUTS = {

    "Half page (8 × 5 in)": PageLayout(
        "half",
        8.0,
        5.0
    ),

    "Full page (8 × 10.5 in)": PageLayout(
        "full",
        8.0,
        10.5
    )

}


def fitted_size_px(
    width,
    height,
    layout,
    dpi=300
):

    scale = min(
        layout.content_width_in / width,
        layout.content_height_in / height
    )

    output_width = round(
        width * scale * dpi
    )

    output_height = round(
        height * scale * dpi
    )

    return (
        max(1, output_width),
        max(1, output_height)
    )
