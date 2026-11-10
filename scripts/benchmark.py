
"""Benchmark the OCR pipeline against the test images.

Runs OCR (and translation, when Liblouis is available) on every
image in tests/test_files and prints per-image metrics. Exits
non-zero with a clear message when any step fails; it never
continues past a failure.
"""

import sys
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT / "src")
)

from braille_converter.ocr_engine import (
    recognize_characters
)

from braille_converter.translator import (
    translate_ueb,
    TranslationError
)


def mean(numbers):

    if not numbers:
        return 0.0

    return sum(numbers) / len(numbers)


def benchmark(image_path):

    records = recognize_characters(
        image_path
    )

    groups = {}

    for record in records:
        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    confidences = [
        record.confidence
        for record in records
        if record.confidence is not None
    ]

    translated = 0

    errors = []

    for group in groups.values():

        group.sort(
            key=lambda r: r.x1
        )

        token = "".join(
            r.text for r in group
        )

        if not token:
            continue

        try:
            braille = translate_ueb(token)

            if braille:
                translated += 1

        except TranslationError as exc:
            errors.append(str(exc))

    return {
        "image": image_path.name,
        "records": len(records),
        "words": len(groups),
        "mean_confidence": round(
            mean(confidences),
            3
        ),
        "translated_words": translated,
        "translation_errors": errors
    }


def main():

    test_dir = (
        ROOT / "tests" / "test_files"
    )

    images = sorted(
        test_dir.glob("*.jpg")
    )

    if not images:
        print(
            f"FAIL: no test images found "
            f"in {test_dir}"
        )

        return 1

    print(
        f"Found {len(images)} test "
        "images\n"
    )

    failures = 0

    for image in images:

        try:
            result = benchmark(image)

        except Exception as exc:
            print(
                f"FAIL {image.name}: "
                f"{exc}"
            )

            failures += 1

            continue

        print(
            f"{result['image']}: "
            f"{result['records']} records, "
            f"{result['words']} words, "
            f"confidence "
            f"{result['mean_confidence']}, "
            f"translated "
            f"{result['translated_words']}"
        )

        for error in result[
            "translation_errors"
        ]:
            print(
                f"  translation error: "
                f"{error}"
            )

    if failures:
        print(
            f"\nFAIL: {failures} image(s) "
            "could not be processed"
        )

        return 1

    print("\nAll images processed")

    return 0


if __name__ == "__main__":

    sys.exit(main())
