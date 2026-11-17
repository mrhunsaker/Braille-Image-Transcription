
"""Unit tests for the shared OCR-to-Braille pipeline rules.

No external tools are needed: Liblouis is replaced by a
stub, so these tests always run.
"""

import pytest

from braille_converter import pipeline as pipeline_module

from braille_converter.models import OCRRecord

from braille_converter.pipeline import (
    export_readiness,
    group_by_word,
    translate_records
)

from braille_converter.translator import (
    TranslationError
)


def make_record(
    record_id,
    text,
    x1,
    group_id,
    kind="literary"
):

    return OCRRecord(
        id=record_id,
        text=text,
        x1=x1,
        y1=0,
        x2=x1 + 10,
        y2=10,
        kind=kind,
        group_id=group_id
    )


def test_group_by_word_preserves_encounter_order():

    first = make_record(1, "a", 0, "g1")

    second = make_record(2, "b", 20, "g2")

    third = make_record(3, "c", 10, "g1")

    groups = group_by_word([first, second, third])

    assert list(groups) == ["g1", "g2"]

    assert groups["g1"] == [first, third]


def test_braille_is_stored_once_per_group(monkeypatch):

    monkeypatch.setattr(
        pipeline_module,
        "translate_ueb",
        lambda token, math_mode=False: (
            f"<{token}>"
        )
    )

    later = make_record(1, "b", 20, "g1")

    earlier = make_record(2, "a", 10, "g1")

    other = make_record(3, "z", 0, "g2")

    records = [later, earlier, other]

    translate_records(records)

    assert earlier.braille == "<ab>"

    assert later.braille == ""

    assert other.braille == "<z>"


def test_math_record_selects_math_table(monkeypatch):

    seen = {}

    def fake_translate(token, math_mode=False):

        seen[token] = math_mode

        return "⠿"

    monkeypatch.setattr(
        pipeline_module,
        "translate_ueb",
        fake_translate
    )

    records = [
        make_record(
            1,
            "x",
            0,
            "g1",
            kind="math"
        ),
        make_record(2, "y", 20, "g2")
    ]

    translate_records(records)

    assert seen["x"] is True

    assert seen["y"] is False


def test_force_math_overrides_literary(monkeypatch):

    seen = {}

    def fake_translate(token, math_mode=False):

        seen[token] = math_mode

        return "⠿"

    monkeypatch.setattr(
        pipeline_module,
        "translate_ueb",
        fake_translate
    )

    translate_records(
        [make_record(1, "x", 0, "g1")],
        force_math=True
    )

    assert seen["x"] is True


def test_export_readiness_classifies_groups():
    """Validation and export must agree on every group."""

    fully_done = make_record(1, "a", 0, "g1")
    fully_done.braille = "⠁"

    untranslated = make_record(2, "b", 20, "g2")

    partial_first = make_record(3, "c", 40, "g3")
    partial_first.braille = "⠉"

    partial_second = make_record(4, "d", 50, "g3")
    partial_second.approved = False

    skipped = make_record(5, "e", 60, "g4")
    skipped.approved = False

    readiness = export_readiness([
        fully_done,
        untranslated,
        partial_first,
        partial_second,
        skipped
    ])

    assert readiness["renderable"] == [[fully_done]]

    assert readiness["untranslated"] == [[untranslated]]

    assert readiness["partial"] == [
        [partial_first, partial_second]
    ]

    assert readiness["skipped"] == [[skipped]]


def test_empty_translation_is_loud(monkeypatch):

    monkeypatch.setattr(
        pipeline_module,
        "translate_ueb",
        lambda token, math_mode=False: ""
    )

    with pytest.raises(TranslationError):

        translate_records(
            [make_record(1, "x", 0, "g1")]
        )
