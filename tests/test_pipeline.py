
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
    translate_ueb
)

TEST_DIR = Path(
    __file__
).parent / "test_files"

EXPECTED_DIR = (
    TEST_DIR / "expected"
)


def load_expected(stem, version=None, exact=False):
    """Load fixtures for a Tesseract version.

    Exact comparisons require a fixture recorded with
    the installed version. Version-independent checks
    can fall back to any recorded version.
    """

    path = None

    if version:
        candidate = (
            EXPECTED_DIR
            / version
            / f"{stem}.json"
        )

        if candidate.exists():
            path = candidate

    if path is None and not exact:
        candidates = sorted(
            EXPECTED_DIR.glob(f"*/{stem}.json")
        )

        if candidates:
            path = candidates[0]

    if path is None:
        pytest.skip(
            f"No expected data for {stem} "
            f"with Tesseract {version}. "
            "Run scripts/generate_expected.py "
            "to record fixtures for this version."
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if exact and payload.get(
        "tesseract_version"
    ) != version:
        pytest.skip(
            "Fixture version does not match "
            "its directory."
        )

    return payload


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


def test_fixture_versions_match_their_directories():

    versions = [
        path
        for path in EXPECTED_DIR.iterdir()
        if path.is_dir()
    ]

    assert versions, (
        "No versioned OCR fixtures were found."
    )

    image_stems = {
        path.stem
        for path in TEST_DIR.glob("*.jpg")
    }

    for version_dir in versions:

        fixtures = sorted(
            version_dir.glob("*_img.json")
        )

        assert fixtures, (
            f"{version_dir.name} has no fixtures."
        )

        for fixture in fixtures:

            assert fixture.stem in image_stems, (
                f"{fixture.name} has no source image."
            )

            payload = json.loads(
                fixture.read_text(encoding="utf-8")
            )

            assert payload[
                "tesseract_version"
            ] == version_dir.name, (
                f"{fixture} is in the wrong "
                "version directory."
            )


def test_exemplar_ground_truth_is_recorded():

    """Human-provided transcriptions are kept separate from
    generated, human-review-pending regression fixtures.
    """

    ground_truth_dir = TEST_DIR / "ground_truth"

    fixtures = sorted(
        ground_truth_dir.glob("*.json")
    )

    assert len(fixtures) >= 2

    for fixture in fixtures:

        payload = json.loads(
            fixture.read_text(encoding="utf-8")
        )

        assert payload["verified_by"]

        assert payload["reading_order"] in {
            "top_to_bottom",
            "left_to_right"
        }

        assert payload["regions"]

        assert all(
            region["text"]
            for region in payload["regions"]
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
        image_path.stem,
        tesseract_version_string,
        exact=True
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
    ocr_records,
    tesseract_version_string
):
    """Catch a catastrophic OCR regression on any version.

    Counts vary between Tesseract versions, but a
    pipeline change that breaks detection entirely must
    fail here even when the exact expectation test is
    skipped for a version mismatch.
    """

    expected = load_expected(
        image_path.stem,
        tesseract_version_string
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



