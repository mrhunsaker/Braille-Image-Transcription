
"""GUI tests driving the real NiceGUI app in a simulation.

The app is built by ConverterApp exactly as the "/" page
builds it, and the real workflow handlers are invoked
(open_image, run_ocr, translate_all, export). Everything
is asserted through UI state, so a broken label, dialog,
or table breaks the test.

Tesseract-dependent tests skip with a clear reason when
Tesseract is not installed.
"""

import io
from pathlib import Path

import pytest

from nicegui.testing import user_simulation

from braille_converter import gui as gui_module

from braille_converter.gui import ConverterApp

from braille_converter.models import OCRRecord

TEST_DIR = Path(__file__).parent / "test_files"

# A worksheet image whose real content the pipeline
# detects reliably.
SAMPLE_IMAGE = (
    TEST_DIR
    / "67020988167474f5810b295ba0fdc993_img.jpg"
)


class FakeUpload:

    """Minimal stand-in for events.UploadEventArguments."""

    def __init__(self, path):

        self.name = path.name

        self.content = io.BytesIO(
            path.read_bytes()
        )


def make_root(holder):

    """Return a root function that keeps the app instance."""

    def root():

        holder["app"] = ConverterApp()

    return root


async def test_page_renders_core_sections():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        await user.should_see(
            "Braille Converter - OCR Review"
        )

        await user.should_see(
            "OCR Character Review"
        )

        await user.should_see(
            "Selected Character"
        )

        await user.should_see(
            "Output Settings"
        )

        await user.should_see("Translate all")

        await user.should_see("Export all")


async def test_startup_status_is_reported(
    tesseract_available
):

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        status = app.status_label.text

        assert status, (
            "Startup validation left no status "
            "message; failures must never be silent."
        )

        if tesseract_available:

            assert (
                "Environment checks passed"
                in status
            )

        else:

            await user.should_see(
                "Startup problems detected"
            )


async def test_run_ocr_without_image_shows_error():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        user.find("Run OCR").click()

        await user.should_see("No image")

        await user.should_see("Open an image first.")

        user.find("Close").click()

        # The status region keeps the last error text
        # (with aria-live) so the user can re-read it;
        # the dialog itself is what closes. Verify the
        # acknowledgement left a status message behind.
        assert "No image" in holder["app"].status_label.text


async def test_export_without_data_shows_error():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        user.find("Export all").click()

        await user.should_see("Nothing to export")

        user.find("Close").click()


@pytest.mark.tesseract
async def test_full_workflow_creates_all_outputs(
    tmp_path
):

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        # Handlers call ui.run_javascript, which needs
        # a client slot; run inside the page's status
        # label slot so the call has a target.
        with app.status_label:

            app.open_image(
                FakeUpload(SAMPLE_IMAGE)
            )

            assert "Loaded" in (
                app.status_label.text
            )

            app.run_ocr()

            assert app.records, (
                "OCR produced no records for "
                f"{SAMPLE_IMAGE.name}"
            )

            assert len(app.table.rows) == len(
                app.records
            )

            app.translate_all()

            translated = [
                record
                for record in app.records
                if record.braille
            ]

            assert translated, (
                "No record received Braille"
            )

            app.output_input.set_value(
                str(tmp_path)
            )

            app.export()

            assert "Export completed" in (
                app.status_label.text
            )

        written = sorted(
            path.suffix
            for path in tmp_path.iterdir()
        )

        assert written == [
            ".json",
            ".pdf",
            ".png",
            ".svg",
        ], written


async def test_apply_edit_requires_selection():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        user.find("Apply changes").click()

        await user.should_see("No record selected")

        user.find("Close").click()


@pytest.mark.tesseract
async def test_keyboard_selection_drives_the_editor():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        with app.status_label:

            app.open_image(FakeUpload(SAMPLE_IMAGE))

            app.run_ocr()

        assert app.records

        target = app.records[0]

        # The Record ID control is the keyboard path;
        # choosing an ID loads and applies the edits.
        app.record_select.set_value(target.id)

        assert app.text_input.value == target.text

        assert app.kind_select.value == target.kind

        assert app.status_label.text.startswith(
            "Editing record"
        )

        app.text_input.set_value("Z")

        app.kind_select.set_value("math")

        app.apply_edit()

        assert target.text == "Z"

        assert target.kind == "math"

        row = next(
            row for row in app.table.rows
            if row["id"] == target.id
        )

        assert row["text"] == "Z"

        assert row["kind"] == "math"

        assert (
            f"Updated record {target.id}"
            in app.status_label.text
        )


@pytest.mark.tesseract
async def test_export_blocks_when_groups_untranslated():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        with app.status_label:

            app.open_image(FakeUpload(SAMPLE_IMAGE))

            app.run_ocr()

            # Export before translating must refuse,
            # naming the number of untranslated words.
            app.export()

            assert "Untranslated records" in (
                app.status_label.text
            )

            assert "approved word(s)" in (
                app.status_label.text
            )


async def test_upload_has_accessible_name_and_accept_filter():
    """The uploader needs a name and an image filter.

    Quasar names its hidden file input generically, so
    the uploader itself must carry a visible label and
    an aria-label.
    """

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        assert app.upload.label == "Choose image file"

        assert app.upload.props.get(
            "aria-label"
        ) == "Choose an image file to open"

        assert app.upload.props.get(
            "accept"
        ) == "image/*"

        await user.should_see("Open image")


async def test_editing_word_clears_stale_braille():
    """An edit must invalidate Braille derived from old text."""

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        app.image_path = SAMPLE_IMAGE

        app.records = [
            OCRRecord(
                id=1,
                text="a",
                x1=0,
                y1=0,
                x2=5,
                y2=5,
                group_id="g1",
                braille="⠁"
            ),
            OCRRecord(
                id=2,
                text="b",
                x1=6,
                y1=0,
                x2=10,
                y2=5,
                group_id="g1"
            ),
            OCRRecord(
                id=3,
                text="c",
                x1=12,
                y1=0,
                x2=18,
                y2=5,
                group_id="g2",
                braille="⠉"
            )
        ]

        app.populate_table()

        with app.status_label:

            app.record_select.set_value(1)

            app.text_input.set_value("x")

            app.apply_edit()

            assert "cleared" in (
                app.status_label.text
            )

            assert app.records[0].braille == ""

            assert app.records[1].braille == ""

            # The edited group is invalidated, but a
            # different word keeps its translation.
            assert app.records[2].braille == "⠉"

            app.export()

            assert "Untranslated records" in (
                app.status_label.text
            )

        await user.should_see("Untranslated records")


async def test_ocr_with_no_records_shows_error(
    monkeypatch
):
    """Zero detections must be reported, never silent."""

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        monkeypatch.setattr(
            gui_module,
            "recognize_characters",
            lambda path: []
        )

        with app.status_label:

            app.image_path = SAMPLE_IMAGE

            app.run_ocr()

            assert app.records == []

            assert app.table.rows == []

            assert "No characters found" in (
                app.status_label.text
            )

        await user.should_see("No characters found")

        await user.should_see(
            "OCR found no characters in this image."
        )
