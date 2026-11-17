
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


def export_readiness(records):
    """Classify word groups for export.

    Export renders one Braille string per word group, and the
    GUI's validation must use exactly the same rules. A group
    is renderable only when every character is approved and at
    least one record carries Braille.

    Returns a dict of group lists:

    - renderable: safe to draw.
    - untranslated: fully approved, but no Braille yet.
    - partial: some characters approved, some not. These
      must be reported loudly, never silently dropped.
    - skipped: no character approved, deliberately excluded.
    """

    result = {
        "renderable": [],
        "untranslated": [],
        "partial": [],
        "skipped": []
    }

    for group in group_by_word(records).values():

        approved = [
            record
            for record in group
            if record.approved
        ]

        if not approved:
            result["skipped"].append(group)

            continue

        if len(approved) != len(group):
            result["partial"].append(group)

            continue

        braille = next(
            (
                record.braille
                for record in group
                if record.braille
            ),
            ""
        )

        if braille:
            result["renderable"].append(group)

        else:
            result["untranslated"].append(group)

    return result


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

        # TODO: preserve inter-word and line spacing in the
        # returned Braille by using record box geometry.
        # Tracked in TODO.md; deferred from the OCR review work.
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
