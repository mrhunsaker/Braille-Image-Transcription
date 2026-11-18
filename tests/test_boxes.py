"""Tests for manually created and provisionally accepted boxes."""

from braille_converter.boxes import (
    ORIGIN_CANDIDATE,
    ORIGIN_MANUAL,
    new_box_record,
    next_record_id,
    normalize_box
)

from braille_converter.models import OCRRecord


def test_records_default_to_ocr_origin():

    record = OCRRecord(
        id=1,
        text="a",
        x1=0,
        y1=0,
        x2=1,
        y2=1
    )

    assert record.origin == "ocr"

    assert record.to_dict()["origin"] == "ocr"


def test_normalize_box_orders_and_clamps():

    assert normalize_box(
        80, 60, 10, 20, (100, 50)
    ) == (10, 20, 80, 50)


def test_normalize_box_rejects_degenerate_size():

    assert normalize_box(
        10, 10, 10, 10, (100, 100)
    ) == (10, 10, 12, 12)

    assert normalize_box(
        99, 99, 99, 99, (100, 100)
    ) == (98, 98, 100, 100)


def test_next_record_id_skips_existing_ids():

    records = [
        OCRRecord(
            id=4,
            text="a",
            x1=0,
            y1=0,
            x2=1,
            y2=1
        )
    ]

    assert next_record_id(records) == 5

    assert next_record_id([]) == 1


def test_new_box_record_is_ready_for_review():

    existing = [
        OCRRecord(
            id=3,
            text="a",
            x1=0,
            y1=0,
            x2=1,
            y2=1,
            braille="⠁"
        )
    ]

    record = new_box_record(
        (10, 20, 40, 30),
        existing,
        ORIGIN_MANUAL
    )

    assert record.id == 4

    assert record.origin == ORIGIN_MANUAL

    assert (record.x1, record.y1, record.x2, record.y2) == (
        10, 20, 40, 30
    )

    assert record.text == ""

    assert record.braille == ""

    assert record.approved

    assert record.group_id == "manual-4"


def test_candidate_records_keep_their_provenance():

    record = new_box_record(
        (5, 5, 25, 15),
        [],
        ORIGIN_CANDIDATE
    )

    assert record.origin == ORIGIN_CANDIDATE

    assert record.group_id == "candidate-1"
