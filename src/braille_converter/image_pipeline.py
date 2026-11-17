
from pathlib import Path
import json

import cv2
import numpy as np

from PIL import Image, ImageDraw

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .braille_render import (
    BrailleProfile,
    draw_braille,
    write_tactile_svg
)

from .layout import PageLayout, fitted_size_px

from .pipeline import export_readiness


class ExportError(RuntimeError):
    """Raised when the records are not safe to export."""


def remove_text_inpaint(image, records):

    rgb = np.array(
        image.convert("RGB")
    )

    mask = np.zeros(
        rgb.shape[:2],
        dtype=np.uint8
    )

    for record in records:

        if not record.approved:
            continue

        pad = max(
            2,
            round(
                min(
                    record.x2 - record.x1,
                    record.y2 - record.y1
                ) * 0.18
            )
        )

        x1 = max(0, record.x1 - pad)

        y1 = max(0, record.y1 - pad)

        x2 = min(
            mask.shape[1] - 1,
            record.x2 + pad
        )

        y2 = min(
            mask.shape[0] - 1,
            record.y2 + pad
        )

        cv2.rectangle(
            mask,
            (x1, y1),
            (x2, y2),
            255,
            -1
        )

    bgr = cv2.cvtColor(
        rgb,
        cv2.COLOR_RGB2BGR
    )

    result = cv2.inpaint(
        bgr,
        mask,
        3,
        cv2.INPAINT_TELEA
    )

    return Image.fromarray(
        cv2.cvtColor(
            result,
            cv2.COLOR_BGR2RGB
        )
    )


def draw_bounding_boxes(image, records):
    """Return a copy of the image with OCR boxes drawn.

    Green boxes are approved records and red boxes are
    rejected records. The image is never modified in place.
    """

    marked = image.convert("RGB").copy()

    draw = ImageDraw.Draw(marked)

    width, height = marked.size

    approved_color = (0, 190, 0)

    rejected_color = (220, 40, 40)

    for record in records:

        x1 = max(0, min(record.x1, width - 1))

        y1 = max(0, min(record.y1, height - 1))

        # OCR records use exclusive x2/y2; Pillow's
        # rectangle uses inclusive coordinates.
        x2 = max(x1, min(record.x2 - 1, width - 1))

        y2 = max(y1, min(record.y2 - 1, height - 1))

        color = (
            approved_color
            if record.approved
            else rejected_color
        )

        draw.rectangle(
            (x1, y1, x2, y2),
            outline=color,
            width=2
        )

        draw.text(
            (x1, max(0, y1 - 13)),
            str(record.id),
            fill=color,
            stroke_width=1,
            stroke_fill=(255, 255, 255)
        )

    return marked


def _render_braille_page(
    original,
    records,
    layout,
    profile,
    renderable
):
    """Build the altered page shared by preview and export."""

    cleaned = remove_text_inpaint(
        original,
        records
    )

    output_width, output_height = fitted_size_px(
        original.width,
        original.height,
        layout,
        profile.dpi
    )

    page = cleaned.resize(
        (output_width, output_height),
        Image.Resampling.LANCZOS
    )

    scale_x = output_width / original.width

    scale_y = output_height / original.height

    draw = ImageDraw.Draw(page)

    for group in renderable:

        ordered = sorted(
            group,
            key=lambda record: record.x1
        )

        braille = next(
            record.braille
            for record in ordered
            if record.braille
        )

        x = round(
            min(record.x1 for record in ordered)
            * scale_x
        )

        y = round(
            min(record.y1 for record in ordered)
            * scale_y
        )

        draw_braille(
            draw,
            x,
            y,
            braille,
            profile
        )

    return page


def render_altered_image(
    original,
    records,
    layout,
    profile
):
    """Render the altered preview without writing files.

    Unlike export, this accepts partially reviewed records so
    the preview can guide the user. Only fully approved,
    translated words are drawn in Braille, matching export.
    """

    readiness = export_readiness(records)

    page = _render_braille_page(
        original,
        records,
        layout,
        profile,
        readiness["renderable"]
    )

    return page, readiness


def _require_export_readiness(records):

    readiness = export_readiness(records)

    if readiness["partial"]:

        raise ExportError(
            f"{len(readiness['partial'])} word(s) are "
            "only partly approved. Approve or reject "
            "every character in each word before "
            "exporting; partially approved words are "
            "never silently dropped."
        )

    if readiness["untranslated"]:

        raise ExportError(
            f"{len(readiness['untranslated'])} approved "
            "word(s) have no Braille. Translate them "
            "before exporting."
        )

    return readiness


def export_json(
    path,
    source_path,
    original_size,
    output_size,
    records
):

    payload = {

        "schema_version": "1.0",

        "source_image": str(source_path),

        "original_dimensions_px": {
            "width": original_size[0],
            "height": original_size[1]
        },

        "output_dimensions_px": {
            "width": output_size[0],
            "height": output_size[1]
        },

        "coordinate_system": (
            "Original image pixels, top-left origin. "
            "x2/y2 are exclusive."
        ),

        "records": [
            record.to_dict()
            for record in records
        ],

        "notes": [

            "OCR confidence is inherited from the "
            "containing word.",

            "Mathematical structure requires human review.",

            "Braille transcription is stored as Unicode.",

            "Coordinates refer to the original image."

        ]

    }

    Path(path).write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def export_outputs(
    source_path,
    records,
    output_dir,
    layout: PageLayout,
    profile: BrailleProfile
):

    source_path = Path(source_path)

    output_dir = Path(output_dir)

    # Validate before creating directories or writing any
    # artifact, so a rejected export leaves no partial set.
    readiness = _require_export_readiness(records)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    base = source_path.stem

    # Release the file handle deterministically; Windows
    # will not clean up an upload directory with an open
    # image inside it.
    with Image.open(source_path) as opened:

        original = opened.convert("RGB")

    page = _render_braille_page(
        original,
        records,
        layout,
        profile,
        readiness["renderable"]
    )

    output_width, output_height = page.size

    # 1. PNG output.
    png_path = output_dir / f"{base}_braille.png"

    page.save(
        png_path,
        dpi=(profile.dpi, profile.dpi)
    )

    # 2. PDF output.
    pdf_path = output_dir / f"{base}_braille.pdf"

    pdf = canvas.Canvas(
        str(pdf_path),
        pagesize=letter
    )

    page_width, page_height = letter

    margin = 0.25 * 72

    max_width = page_width - 2 * margin

    max_height = page_height - 2 * margin

    image_width_in = output_width / profile.dpi

    image_height_in = output_height / profile.dpi

    factor = min(
        max_width / (image_width_in * 72),
        max_height / (image_height_in * 72)
    )

    draw_width = image_width_in * 72 * factor

    draw_height = image_height_in * 72 * factor

    pdf.drawImage(
        str(png_path),
        (page_width - draw_width) / 2,
        (page_height - draw_height) / 2,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True
    )

    pdf.showPage()

    pdf.save()

    # 3. JSON output.
    json_path = output_dir / f"{base}_ocr.json"

    export_json(
        json_path,
        source_path,
        original.size,
        page.size,
        records
    )

    # 4. Tactile SVG output.
    tactile_path = output_dir / f"{base}_tactile.svg"

    # The tactile SVG must contain the same words as the
    # raster outputs; unapproved words are not embossed.
    write_tactile_svg(
        tactile_path,
        [
            record
            for group in readiness["renderable"]
            for record in group
        ],
        profile,
        original.size,
        page.size
    )

    return [
        png_path,
        pdf_path,
        json_path,
        tactile_path
    ]
