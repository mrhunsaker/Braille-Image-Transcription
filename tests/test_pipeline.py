
"""Integration tests against tests/test_files images.

These run the real OCR pipeline and compare against the
expected data in tests/test_files/expected/. They skip
with a clear reason when Tesseract or Liblouis is not
installed on the machine.

Exact record and word counts depend on the Tesseract
version, so the expectation test runs only when this
machine's version matches the version recorded in the
expected data. Version-independent checks (ordering,
tokens, determinism, a minimum word count) always run
when Tesseract is present.
"""

import json
from pathlib import Path

import pytest

from braille_converter.ocr_engine import (
    recognize_characters
)

from braille_converter.translator import (
    load_env_file,
    translate_ueb
)

TEST_DIR = Path(
    __file__
).parent / "test_files"

EXPECTED_DIR = (
    TEST_DIR / "expected"
)


def load_expected(stem):

    path = (
        EXPECTED_DIR / f"{stem}.json"
    )

    if not path.exists():
        pytest.skip(
            f"No expected data for "
            f"{stem}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def group_records(records):

    groups = {}

    for record in records:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    return groups


def record_signature(records):

    return tuple(
        (
            record.text,
            record.group_id,
            record.x1,
            record.y1,
            record.x2,
            record.y2
        )
        for record in records
    )


@pytest.fixture(
    params=sorted(
        TEST_DIR.glob("*.jpg")
    ),
    ids=lambda path: path.stem
)
def image_path(request):

    return request.param


@pytest.mark.tesseract
def test_records_match_expected(
    image_path,
    ocr_records,
    tesseract_version_string
):

    expected = load_expected(
        image_path.stem
    )

    recorded = expected.get(
        "tesseract_version"
    )

    if (
        recorded
        and recorded != tesseract_version_string
    ):

        pytest.skip(
            f"Expected data was recorded "
            f"with Tesseract {recorded}; "
            f"this machine has "
            f"{tesseract_version_string}"
        )

    records = ocr_records(image_path)

    assert len(records) == (
        expected["record_count"]
    ), (
        f"expected "
        f"{expected['record_count']} "
        f"records, got "
        f"{len(records)}"
    )

    groups = group_records(records)

    assert len(groups) == (
        expected["word_count"]
    ), (
        f"expected "
        f"{expected['word_count']} "
        f"groups, got "
        f"{len(groups)}"
    )


@pytest.mark.tesseract
def test_minimum_words_detected(
    image_path,
    ocr_records
):
    """Catch a catastrophic OCR regression on any version.

    Counts vary between Tesseract versions, but a
    pipeline change that breaks detection entirely must
    fail here even when the exact expectation test is
    skipped for a version mismatch.
    """

    expected = load_expected(
        image_path.stem
    )

    groups = group_records(
        ocr_records(image_path)
    )

    minimum = expected["min_word_count"]

    assert len(groups) >= minimum, (
        f"expected at least {minimum} "
        f"word groups, got {len(groups)}"
    )


@pytest.mark.tesseract
def test_records_are_deterministic(image_path):
    """The same image must produce the same result twice.

    Runs OCR directly instead of through the session
    cache, because caching would hide nondeterminism.
    """

    first = record_signature(
        recognize_characters(image_path)
    )

    second = record_signature(
        recognize_characters(image_path)
    )

    assert first == second, (
        f"OCR output for "
        f"{image_path.name} changed "
        "between identical runs"
    )


@pytest.mark.tesseract
def test_records_are_ordered(
    image_path,
    ocr_records
):

    positions = {}

    for record in ocr_records(image_path):

        positions.setdefault(
            record.group_id,
            []
        ).append(record.x1)

    for group_id, x_positions in (
        positions.items()
    ):

        assert (
            x_positions
            == sorted(x_positions)
        ), (
            f"group {group_id} "
            "characters are not "
            "in left-to-right order"
        )


@pytest.mark.tesseract
def test_words_join_to_tokens(
    image_path,
    ocr_records
):

    groups = group_records(
        ocr_records(image_path)
    )

    for group in groups.values():

        token = "".join(
            r.text for r in group
        )

        assert token, (
            "empty token for group "
            f"{group[0].group_id}"
        )


@pytest.mark.tesseract
@pytest.mark.liblouis
def test_every_detected_word_translates(
    image_path,
    ocr_records
):

    groups = group_records(
        ocr_records(image_path)
    )

    for group in groups.values():

        token = "".join(
            r.text for r in group
        )

        if not token:
            continue

        braille = translate_ueb(token)

        assert braille, (
            f"token {token!r} "
            "translated to empty "
            "output"
        )


def test_env_file_is_valid():

    env_path = (
        Path(__file__)
        .resolve()
        .parents[1]
        / ".env"
    )

    if not env_path.exists():
        pytest.skip(
            "No .env file on this "
            "machine"
        )

    values = load_env_file()

    assert values, (
        ".env exists but loaded "
        "no values"
    )
