
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


def recognize_characters(image_path):

    configure_tesseract()

    image = Image.open(image_path).convert("RGB")

    width, height = image.size

    # First identify words and their bounding boxes.
    word_data = pytesseract.image_to_data(
        image,
        output_type=Output.DICT,
        config="--psm 11"
    )

    words = []

    for i, text in enumerate(word_data["text"]):

        text = (text or "").strip()

        if not text:
            continue

        try:
            confidence = float(word_data["conf"][i])
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

    # Now identify individual characters.
    # Tesseract uses a bottom-left coordinate origin.
    boxes = pytesseract.image_to_boxes(image)

    records = []

    record_id = 1

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

        # Convert to top-left image coordinates.
        x1 = left
        y1 = height - top
        x2 = right
        y2 = height - bottom

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        # Find the word containing this character.
        matching_word = None

        for word in words:

            if (
                word["x1"] <= center_x <= word["x2"]
                and word["y1"] <= center_y <= word["y2"]
            ):
                matching_word = word
                break

        if matching_word:

            group_id = matching_word["id"]

            source_word = matching_word["text"]

            confidence = matching_word["confidence"]

        else:

            group_id = f"character-{record_id}"

            source_word = char

            confidence = None

        records.append(
            OCRRecord(
                id=record_id,
                text=char,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                confidence=confidence,
                source_word=source_word,
                group_id=group_id
            )
        )

        record_id += 1

    return records
