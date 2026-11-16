
"""Shared OCR-to-Braille pipeline steps.

The GUI and the command-line converter both use this
module so translation rules (one Braille string per word
group, stored on the group's first record) exist in one
place.
"""

from .translator import (
    translate_ueb,
    TranslationError
)


def group_by_word(records):
    """Group records by word, preserving encounter order."""

    groups = {}

    for record in records:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    return groups


def translate_records(records, force_math=False):
    """Translate every word group into Braille in place.

    Braille is stored once per group, on its first record
    in left-to-right order, because exports render one
    Braille string per word.

    force_math uses the math table for every group; by
    default a group uses math when any of its records is
    classified as math.

    Raises TranslationError when Liblouis returns an empty
    translation, so a failure can never be silent.
    """

    for group in group_by_word(records).values():

        group.sort(
            key=lambda record: record.x1
        )

        token = "".join(
            record.text for record in group
        )

        math_mode = force_math or any(
            record.kind == "math"
            for record in group
        )

        translated = translate_ueb(
            token,
            math_mode=math_mode
        )

        if not translated:

            raise TranslationError(
                "Liblouis returned an empty "
                f"translation for token "
                f"{token!r}."
            )

        for index, record in enumerate(group):

            record.braille = (
                translated
                if index == 0
                else ""
            )
