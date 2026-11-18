"""Helpers for creating boxes outside the OCR pass.

Manual boxes and accepted provisional regions become ordinary
``OCRRecord`` objects so review, translation, export readiness and
the clean-image export all work through the same pipeline. The
``origin`` field keeps their provenance visible to reviewers.
"""

from .models import OCRRecord

ORIGIN_OCR = "ocr"
ORIGIN_MANUAL = "manual"
ORIGIN_CANDIDATE = "candidate"

MIN_BOX_SIDE = 2


def normalize_box(x1, y1, x2, y2, image_size):
    """Return a clamped, ordered box in exclusive coordinates.

    x2/y2 are exclusive, matching ``OCRRecord`` and the rest of
    the app. A box smaller than ``MIN_BOX_SIDE`` pixels is widened
    where there is room in the image, so a degenerate drag can
    never create an empty mask.
    """

    width, height = image_size

    raw_x = (
        max(0, min(int(round(x1)), width)),
        max(0, min(int(round(x2)), width))
    )

    raw_y = (
        max(0, min(int(round(y1)), height)),
        max(0, min(int(round(y2)), height))
    )

    left, right = sorted(raw_x)
    top, bottom = sorted(raw_y)

    if left >= right:
        if right + MIN_BOX_SIDE <= width:
            right = left + MIN_BOX_SIDE

        else:
            right = width
            left = max(0, right - MIN_BOX_SIDE)

    if top >= bottom:
        if bottom + MIN_BOX_SIDE <= height:
            bottom = top + MIN_BOX_SIDE

        else:
            bottom = height
            top = max(0, bottom - MIN_BOX_SIDE)

    return (left, top, right, bottom)


def next_record_id(records):
    """Return an ID that does not collide with current records."""

    return max(
        (record.id for record in records),
        default=0
    ) + 1


def new_box_record(box, records, origin):
    """Build an unreviewed record for a new manual/provisional box."""

    record_id = next_record_id(records)

    return OCRRecord(
        id=record_id,
        text="",
        x1=box[0],
        y1=box[1],
        x2=box[2],
        y2=box[3],
        confidence=None,
        kind="literary",
        braille="",
        approved=True,
        source_word="",
        group_id=f"{origin}-{record_id}",
        origin=origin
    )
