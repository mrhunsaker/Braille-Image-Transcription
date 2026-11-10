
"""Integration tests against tests/test_files images.

These run the real OCR pipeline and compare against the
expected data in tests/test_files/expected/. They skip
with a clear reason when Tesseract or Liblouis is not
installed on the machine.
"""

import json
from pathlib import Path

import pytest

from braille_converter.ocr_engine import (
    configure_tesseract,
    recognize_characters
)

from braille_converter.translator import (
    find_lou_translate,
    load_env_file,
    translate_ueb
)

TEST_DIR = Path(
    __file__
).parent / "test_files"

EXPECTED_DIR = (
    TEST_DIR / "expected"
)


def tesseract_available():

    try:
        configure_tesseract()

        import pytesseract

        pytesseract.get_tesseract_version()

        return True

    except Exception:
        return False


def liblouis_available():

    try:
        import louis

        return True

    except ImportError:
        pass

    if find_lou_translate():
        return True

    return False


needs_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract is not "
    "installed on this machine"
)

needs_liblouis = pytest.mark.skipif(
    not liblouis_available(),
    reason="Liblouis with UEB "
    "tables is not installed on "
    "this machine"
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


@pytest.fixture(
    params=sorted(
        TEST_DIR.glob("*.jpg")
    ),
    ids=lambda path: path.stem
)
def image_path(request):

    return request.param


@needs_tesseract
def test_records_match_expected(
    image_path
):

    expected = load_expected(
        image_path.stem
    )

    records = recognize_characters(
        image_path
    )

    assert len(records) == (
        expected["record_count"]
    ), (
        f"expected "
        f"{expected['record_count']} "
        f"records, got "
        f"{len(records)}"
    )

    groups = {}

    for record in records:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    assert len(groups) == (
        expected["word_count"]
    ), (
        f"expected "
        f"{expected['word_count']} "
        f"groups, got "
        f"{len(groups)}"
    )


@needs_tesseract
def test_records_are_ordered(image_path):

    records = recognize_characters(
        image_path
    )

    positions = {}

    for record in records:

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


@needs_tesseract
def test_words_join_to_tokens(image_path):

    records = recognize_characters(
        image_path
    )

    groups = {}

    for record in records:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

    for group in groups.values():

        token = "".join(
            r.text for r in group
        )

        assert token, (
            "empty token for group "
            f"{group[0].group_id}"
        )


@needs_liblouis
def test_every_detected_word_translates(
    image_path
):

    records = recognize_characters(
        image_path
    )

    groups = {}

    for record in records:

        groups.setdefault(
            record.group_id,
            []
        ).append(record)

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
