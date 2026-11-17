
from pathlib import Path
import os
import re
import shutil

import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

from .models import OCRRecord
from .ocr_regions import (
    detect_fraction_parts,
    detect_text_regions
)

from .translator import load_env_file


REGION_CROP_PAD = 6

REGION_UPSCALE = 3

REGION_MIN_CONFIDENCE = 0.55

FRACTION_SEARCH_DISTANCE = 30

FRACTION_MIN_CONFIDENCE = 0.2


# Characters relevant to the application.
ALLOWED_SYMBOLS = set(
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "√"
    "+-=()[]{}.,*/^_"
    "<>≤≥×÷"
    "?!:;'\"#%&~@"
    "°¼½¾"
    "≠≈±∓→←↔∈∉∑∫∂∞"
)


# Slash is deliberately absent: numeric fractions such as
# 1/4 use UEB fraction indicators in the literary table and
# translate incorrectly through the math table.
MATH_SYMBOLS = set(
    "+-=()[]{}*^_"
    "<>≤≥×÷√"
    "≠≈±∓→←↔∈∉∑∫∂∞"
)

FRACTION_RE = re.compile(
    r"^\d+(?:\s+\d+)?/\d+$|^\d+[¼½¾]$"
)


def suggest_kind(text):
    """Return 'math' only for genuinely mathematical tokens."""

    token = text.strip()

    if FRACTION_RE.fullmatch(token):

        return "literary"

    if any(
        char in MATH_SYMBOLS
        for char in token
    ):
        return "math"

    return "literary"


# Page segmentation mode for both word and character
# detection. Measurements on tests/test_files show
# --psm 6 (uniform block of text) detects substantially
# more real words than --psm 11 (sparse text) on these
# worksheet images, and using one mode for both calls
# keeps word and character boxes on the same
# segmentation so they can be matched reliably.
PSM_MODE = "--psm 6"


def configure_tesseract():

    configured = os.environ.get("TESSERACT_CMD")

    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured

    elif not shutil.which("tesseract"):

        candidate = Path(
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)


class WordIndex:
    """Bucketed lookup from character centers to words."""

    def __init__(self, words):

        self.words = words

        # Grid of bucket size 32 px. Words are
        # registered in every bucket their box
        # overlaps, so containment lookups only
        # inspect nearby words.
        self.bucket_size = 32

        self.buckets = {}

        for word in words:

            x1 = word["x1"] // self.bucket_size

            x2 = word["x2"] // self.bucket_size

            y1 = word["y1"] // self.bucket_size

            y2 = word["y2"] // self.bucket_size

            for bx in range(x1, x2 + 1):

                for by in range(y1, y2 + 1):

                    self.buckets.setdefault(
                        (bx, by),
                        []
                    ).append(word)

    def find(self, center_x, center_y):
        """Return the word containing the point, or None."""

        bucket = self.buckets.get(
            (
                center_x // self.bucket_size,
                center_y // self.bucket_size
            )
        )

        if not bucket:
            return None

        for word in bucket:

            if (
                word["x1"] <= center_x <= word["x2"]
                and word["y1"] <= center_y <= word["y2"]
            ):
                return word

        return None


def detect_words(image, config=PSM_MODE):
    """Return word dicts from image_to_data."""

    word_data = pytesseract.image_to_data(
        image,
        output_type=Output.DICT,
        config=config
    )

    words = []

    for i, text in enumerate(word_data["text"]):

        text = (text or "").strip()

        if not text:
            continue

        try:
            confidence = float(
                word_data["conf"][i]
            )

        except (ValueError, TypeError):
            confidence = -1

        if confidence < 0:
            confidence = None

        else:
            confidence = confidence / 100.0

        x = int(word_data["left"][i])

        y = int(word_data["top"][i])

        w = int(word_data["width"][i])

        h = int(word_data["height"][i])

        words.append({
            "id": f"word-{i}",
            "text": text,
            "x1": x,
            "y1": y,
            "x2": x + w,
            "y2": y + h,
            "confidence": confidence
        })

    return words


def detect_characters(
    image,
    width,
    height,
    config=PSM_MODE
):
    """Return raw character tuples from image_to_boxes.

    Tesseract uses a bottom-left coordinate origin;
    the returned tuples use top-left image coordinates.
    """

    boxes = pytesseract.image_to_boxes(
        image,
        config=config
    )

    characters = []

    for line in boxes.splitlines():

        parts = line.split()

        if len(parts) < 5:
            continue

        char = parts[0]

        if char not in ALLOWED_SYMBOLS:
            continue

        try:
            left, bottom, right, top = map(
                int, parts[1:5]
            )

        except ValueError:
            continue

        characters.append((
            char,
            left,
            height - top,
            right,
            height - bottom
        ))

    return characters


def _enabled(name, default=True):
    """Read a boolean OCR feature switch."""

    load_env_file()

    raw = os.environ.get(name, "").strip().lower()

    if not raw:
        return default

    return raw not in {
        "0",
        "false",
        "no",
        "off"
    }


def _records_from_image(
    image,
    config,
    group_prefix=None,
    offset=(0, 0),
    scale=1
):
    """Run one Tesseract pass and map boxes to the source image."""

    width, height = image.size

    words = detect_words(image, config)

    word_index = WordIndex(words)

    characters = detect_characters(
        image,
        width,
        height,
        config
    )

    ordered_words = sorted(
        words,
        key=lambda word: (
            word["y1"],
            word["x1"]
        )
    )

    word_rank = {
        word["id"]: rank
        for rank, word in enumerate(
            ordered_words
        )
    }

    loose_rank = len(ordered_words)

    prepared = []

    for char, raw_x1, raw_y1, raw_x2, raw_y2 in characters:

        x1 = round(offset[0] + raw_x1 / scale)

        y1 = round(offset[1] + raw_y1 / scale)

        x2 = round(offset[0] + raw_x2 / scale)

        y2 = round(offset[1] + raw_y2 / scale)

        center_x = (raw_x1 + raw_x2) / 2

        center_y = (raw_y1 + raw_y2) / 2

        matching_word = word_index.find(
            center_x,
            center_y
        )

        if matching_word:

            rank = word_rank[
                matching_word["id"]
            ]

            word_id = matching_word["id"]

            if group_prefix:
                word_id = (
                    f"{group_prefix}-{word_id}"
                )

            group_id = word_id

            source_word = matching_word[
                "text"
            ]

            confidence = matching_word[
                "confidence"
            ]

        else:

            rank = loose_rank

            group_id = None

            source_word = char

            confidence = None

        prepared.append({
            "text": char,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "rank": rank,
            "group_id": group_id,
            "source_word": source_word,
            "confidence": confidence,
            "kind": suggest_kind(source_word)
        })

    prepared.sort(
        key=lambda item: (
            item["rank"],
            item["x1"]
        )
    )

    records = []

    for index, item in enumerate(prepared, start=1):

        group_id = (
            item["group_id"]
            or f"character-{group_prefix or 'word'}-{index}"
        )

        records.append(
            OCRRecord(
                id=0,
                text=item["text"],
                x1=item["x1"],
                y1=item["y1"],
                x2=item["x2"],
                y2=item["y2"],
                confidence=item["confidence"],
                kind=item["kind"],
                source_word=item["source_word"],
                group_id=group_id
            )
        )

    return records


def _group_bounds(records):
    """Return the bounding box and token for a record group."""

    token = "".join(
        record.text for record in records
    )

    return (
        min(record.x1 for record in records),
        min(record.y1 for record in records),
        max(record.x2 for record in records),
        max(record.y2 for record in records),
        token.strip().lower()
    )


def _box_overlap(first, second):
    """Return IoU for two four-value bounding boxes."""

    x1 = max(first[0], second[0])

    y1 = max(first[1], second[1])

    x2 = min(first[2], second[2])

    y2 = min(first[3], second[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    overlap = (x2 - x1) * (y2 - y1)

    first_area = (first[2] - first[0]) * (
        first[3] - first[1]
    )

    second_area = (second[2] - second[0]) * (
        second[3] - second[1]
    )

    return overlap / max(
        first_area + second_area - overlap,
        1
    )


def _merge_records(primary, secondary):
    """Add region records that the whole-image pass missed."""

    known = []

    groups = {}

    for record in primary:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    for group in groups.values():

        known.append(_group_bounds(group))

    additions = []

    groups = {}

    for record in secondary:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    for group in groups.values():

        bounds = _group_bounds(group)

        confidences = [
            record.confidence
            for record in group
            if record.confidence is not None
        ]

        if (
            confidences
            and sum(confidences) / len(confidences)
            < REGION_MIN_CONFIDENCE
        ):
            continue

        duplicate = any(
            _box_overlap(bounds[:4], other[:4]) > 0.4
            or (
                bounds[4] == other[4]
                and _box_overlap(
                    bounds[:4],
                    other[:4]
                ) > 0.15
            )
            for other in known
        )

        if duplicate:
            continue

        new_id = f"region-{len(additions) + 1}"

        for record in group:
            record.group_id = new_id

        known.append(bounds)

        additions.extend(group)

    return list(primary) + additions


def _render_component_mask(image, components):
    """Copy only the supplied glyph components onto white."""

    pad = 6

    area = (
        min(component[0] for component in components) - pad,
        min(component[1] for component in components) - pad,
        max(component[2] for component in components) + pad,
        max(component[3] for component in components) + pad
    )

    gray = np.array(image.convert("L"))

    canvas = np.full(
        (
            area[3] - area[1],
            area[2] - area[0]
        ),
        255,
        dtype=np.uint8
    )

    for x1, y1, x2, y2 in components:

        source = gray[
            max(0, y1):y2,
            max(0, x1):x2
        ]

        dx1 = x1 - area[0]

        dy1 = y1 - area[1]

        dx2 = dx1 + source.shape[1]

        dy2 = dy1 + source.shape[0]

        canvas[dy1:dy2, dx1:dx2] = np.where(
            source < 160,
            0,
            255
        )

    return Image.fromarray(canvas, mode="L")


def _ocr_fraction_part(image, components):
    """Recognize one stacked fraction half as digits."""

    if not components:
        return None

    crop = _render_component_mask(
        image,
        components
    )

    crop = crop.resize(
        (
            crop.width * REGION_UPSCALE,
            crop.height * REGION_UPSCALE
        ),
        Image.Resampling.LANCZOS
    )

    best = None

    configs = (
        (
            "--psm 8 "
            "-c tessedit_char_whitelist=0123456789"
        ),
        (
            "--psm 10 "
            "-c tessedit_char_whitelist=0123456789"
        )
    )

    for config in configs:

        data = pytesseract.image_to_data(
            crop,
            config=config,
            output_type=Output.DICT
        )

        for index, text in enumerate(
            data["text"]
        ):

            text = (text or "").strip()

            if (
                not text.isdigit()
                or len(text) > 3
            ):
                continue

            try:
                confidence = float(
                    data["conf"][index]
                )

            except (TypeError, ValueError):
                continue

            if confidence < 0:
                continue

            if (
                best is None
                or confidence > best[1]
            ):
                best = (
                    text,
                    confidence / 100.0
                )

    if best is None:
        return None

    if best[1] < FRACTION_MIN_CONFIDENCE:
        return None

    return best


def _fraction_area(bar):
    """Return the source-image area occupied by a fraction."""

    pad = 8

    return (
        bar[0] - pad,
        max(
            0,
            bar[1] - FRACTION_SEARCH_DISTANCE
        ),
        bar[2] + pad,
        bar[3] + FRACTION_SEARCH_DISTANCE
    )


def _apply_fraction_records(image, records):
    """Normalize stacked fractions to literal slash tokens."""

    if not records:
        return records

    consumed = set()

    additions = []

    for bar, above_parts, below_parts in (
        detect_fraction_parts(image)
    ):

        area = _fraction_area(bar)

        numerator = _ocr_fraction_part(
            image,
            above_parts
        )

        denominator = _ocr_fraction_part(
            image,
            below_parts
        )

        if numerator is None or denominator is None:
            continue

        token = (
            f"{numerator[0]}/{denominator[0]}"
        )

        confidence = (
            numerator[1] + denominator[1]
        ) / 2

        additions.append(
            OCRRecord(
                id=0,
                text=token,
                x1=area[0],
                y1=area[1],
                x2=area[2],
                y2=area[3],
                confidence=confidence,
                kind="literary",
                source_word=token,
                group_id=(
                    f"fraction-{len(additions) + 1}"
                )
            )
        )

        for record in records:

            if id(record) in consumed:
                continue

            center_x = (
                record.x1 + record.x2
            ) / 2

            center_y = (
                record.y1 + record.y2
            ) / 2

            if (
                area[0] <= center_x <= area[2]
                and area[1] <= center_y <= area[3]
                and record.text not in {
                    "?",
                    "g",
                    "r",
                    "o",
                    "u",
                    "p"
                }
            ):
                consumed.add(id(record))

    kept = [
        record
        for record in records
        if id(record) not in consumed
    ]

    return kept + additions


def _finalize_records(records):
    """Assign stable IDs and preserve in-word reading order."""

    groups = {}

    for record in records:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    ordered = []

    for group in groups.values():

        ordered.append(
            sorted(
                group,
                key=lambda record: (
                    record.x1,
                    record.y1
                )
            )
        )

    ordered.sort(
        key=lambda group: (
            min(record.y1 for record in group),
            min(record.x1 for record in group),
            group[0].group_id
        )
    )

    result = []

    for record_id, group in enumerate(
        ordered,
        start=1
    ):

        for record in group:

            record.id = record_id

            result.append(record)

        record_id += len(group) - 1

    return result


def recognize_characters(image_path):
    """Return OCRRecords from whole-image and region passes.

    OpenCV proposes text regions; Tesseract still produces
    every character box. Stacked fractions are normalized to
    ``numerator/denominator`` records so UEB fraction
    indicators are used during translation.
    """

    configure_tesseract()

    # Close the file handle deterministically: on Windows a
    # lingering handle prevents cleanup of upload temp dirs.
    with Image.open(image_path) as opened:

        image = opened.convert("RGB")

    records = _records_from_image(
        image,
        PSM_MODE
    )

    if _enabled("OCR_REGION_DETECTION"):

        for index, region in enumerate(
            detect_text_regions(image),
            start=1
        ):

            x1, y1, x2, y2 = region

            left = max(
                0,
                x1 - REGION_CROP_PAD
            )

            top = max(
                0,
                y1 - REGION_CROP_PAD
            )

            right = min(
                image.width,
                x2 + REGION_CROP_PAD
            )

            bottom = min(
                image.height,
                y2 + REGION_CROP_PAD
            )

            crop = image.crop(
                (left, top, right, bottom)
            )

            scale = REGION_UPSCALE

            crop = crop.resize(
                (
                    crop.width * scale,
                    crop.height * scale
                ),
                Image.Resampling.LANCZOS
            )

            aspect = (
                (right - left)
                / max(bottom - top, 1)
            )

            config = (
                "--psm 8"
                if aspect < 3
                else "--psm 7"
            )

            local = _records_from_image(
                crop,
                config,
                group_prefix=f"r{index}",
                offset=(left, top),
                scale=scale
            )

            records = _merge_records(
                records,
                local
            )

    records = _apply_fraction_records(
        image,
        records
    )

    return _finalize_records(records)
