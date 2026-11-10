
from bisect import bisect_right
from pathlib import Path
import os
import shutil

import pytesseract
from PIL import Image
from pytesseract import Output

from .models import OCRRecord


# Characters relevant to the application.
ALLOWED_SYMBOLS = set(
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "√"
    "+-=()[]{}.,*/^_"
    "<>≤≥×÷"
)


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


def detect_words(image):
    """Return word dicts from image_to_data."""

    word_data = pytesseract.image_to_data(
        image,
        output_type=Output.DICT,
        config=PSM_MODE
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


def detect_characters(image, width, height):
    """Return raw character tuples from image_to_boxes.

    Tesseract uses a bottom-left coordinate origin;
    the returned tuples use top-left image coordinates.
    """

    boxes = pytesseract.image_to_boxes(
        image,
        config=PSM_MODE
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


def recognize_characters(image_path):
    """Return OCRRecords for every allowed character.

    Records are ordered by word (reading order) and then
    by horizontal position, so grouped tokens can be
    reconstructed without re-sorting.
    """

    configure_tesseract()

    image = Image.open(image_path).convert("RGB")

    width, height = image.size

    words = detect_words(image)

    word_index = WordIndex(words)

    characters = detect_characters(
        image,
        width,
        height
    )

    # Word order for stable record ordering:
    # top-to-bottom, then left-to-right.
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

    # Characters not inside any word sort after all
    # word characters, left-to-right.
    loose_rank = len(ordered_words)

    prepared = []

    for char, x1, y1, x2, y2 in characters:

        center_x = (x1 + x2) / 2

        center_y = (y1 + y2) / 2

        matching_word = word_index.find(
            center_x,
            center_y
        )

        if matching_word:
            rank = word_rank[
                matching_word["id"]
            ]

            group_id = matching_word["id"]

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
            "confidence": confidence
        })

    # Stable order: word rank, then x position.
    prepared.sort(
        key=lambda item: (
            item["rank"],
            item["x1"]
        )
    )

    records = []

    record_id = 1

    for item in prepared:

        group_id = (
            item["group_id"]
            or f"character-{record_id}"
        )

        records.append(
            OCRRecord(
                id=record_id,
                text=item["text"],
                x1=item["x1"],
                y1=item["y1"],
                x2=item["x2"],
                y2=item["y2"],
                confidence=item[
                    "confidence"
                ],
                source_word=item[
                    "source_word"
                ],
                group_id=group_id
            )
        )

        record_id += 1

    return records
