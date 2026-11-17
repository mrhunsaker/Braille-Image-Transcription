
from pathlib import Path
import base64
import io
import shutil
import tempfile

from PIL import Image
from nicegui import events, run, ui

from .diagnostics import run_checks

from .ocr_engine import recognize_characters

from .translator import TranslationError

from .upload_validation import UploadError, validate_upload

from .pipeline import export_readiness, translate_records

from .layout import LAYOUTS

from .braille_render import BrailleProfile

from .image_pipeline import (
    draw_bounding_boxes,
    export_outputs,
    render_altered_image
)


PREVIEW_SIZE = (360, 280)

BOX_PREVIEW_SIZE = (360, 280)


def _encoded_preview(image, size, alt):
    """Return a scaled PNG data URI and a safe alt string."""

    preview = image.copy()

    preview.thumbnail(size)

    buffer = io.BytesIO()

    preview.save(buffer, format="PNG")

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    safe_alt = (
        alt.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return (
        f"data:image/png;base64,{encoded}",
        safe_alt
    )


def _box_summary(records):
    """Describe the overlay for screen-reader users."""

    if not records:
        return (
            "Run OCR to see bounding boxes. "
            "No records are available yet."
        )

    parts = [
        f"{len(records)} OCR bounding box(es). ",
        "Green means approved; red means rejected."
    ]

    for record in records[:10]:

        parts.append(
            f" ID {record.id}: "
            f"{record.x1},{record.y1} to "
            f"{record.x2},{record.y2}, "
            + (
                "approved."
                if record.approved
                else "rejected."
            )
        )

    if len(records) > 10:

        parts.append(
            f" {len(records) - 10} more box(es) "
            "are listed in the OCR table."
        )

    return "".join(parts)


def _altered_summary(records, readiness):
    """Explain exactly what the altered preview shows."""

    parts = ["Altered image: approved text removed"]

    rendered = len(readiness["renderable"])

    if rendered:

        parts.append(
            f"; {rendered} translated word(s) "
            "overlaid in Braille"
        )

    else:

        parts.append(
            "; no translated words are overlaid yet"
        )

    if readiness["untranslated"]:

        parts.append(
            f"; {len(readiness['untranslated'])} "
            "approved word(s) still need translation"
        )

    if readiness["partial"]:

        parts.append(
            f"; {len(readiness['partial'])} word(s) "
            "have mixed approvals"
        )

    if readiness["skipped"]:

        parts.append(
            f"; {len(readiness['skipped'])} word(s) "
            "have no approved characters and are "
            "excluded"
        )

    parts.append(".")

    if not records:

        parts.append(
            " Run OCR to create the altered image."
        )

    return "".join(parts)


def _render_visualization_data(
    path,
    records,
    layout,
    profile
):
    """Build all previews off the NiceGUI event loop."""

    with Image.open(path) as opened:

        original = opened.convert("RGB")

    name = Path(path).name

    boxed = draw_bounding_boxes(
        original,
        records
    )

    altered, readiness = render_altered_image(
        original,
        records,
        layout,
        profile
    )

    original_preview = _encoded_preview(
        original,
        PREVIEW_SIZE,
        f"Original image {name}, "
        f"{original.width} by {original.height} "
        "pixels."
    )

    box_preview = _encoded_preview(
        boxed,
        BOX_PREVIEW_SIZE,
        f"Bounding boxes for {name}: "
        + _box_summary(records)
    )

    altered_preview = _encoded_preview(
        altered,
        PREVIEW_SIZE,
        f"Altered image for {name}: "
        + _altered_summary(records, readiness)
    )

    return {
        "original": original_preview,
        "boxed": box_preview,
        "altered": altered_preview,
        "box_summary": _box_summary(records),
        "altered_summary": (
            f"Altered Image Preview for {name}. "
            + _altered_summary(records, readiness)
        )
    }


class ConverterApp:

    """NiceGUI front end for the OCR review workflow."""

    def __init__(self):

        self.image_path = None

        self.records = []

        self._error_source = None

        self._build()

    # ---------------------------------------------------------
    # UI construction.
    # ---------------------------------------------------------

    def _build(self):

        with ui.column().classes("w-full max-w-[1400px] mx-auto gap-2"):

            self._build_header()

            self._build_toolbar()

            self._build_status()

            with ui.row().classes(
                "w-full items-start gap-3"
            ):

                with ui.column().classes(
                    "w-1/3 min-w-[420px]"
                ):

                    self._build_review_table()

                    self._build_editor()

                with ui.column().classes(
                    "w-1/3 min-w-[300px]"
                ):

                    self._build_bounding_boxes()

                with ui.column().classes(
                    "w-1/3 min-w-[520px]"
                ):

                    self._build_previews()

                    self._build_settings()

            self._build_error_dialog()

            self._validate_startup()

    def _build_header(self):

        ui.label(
            "Braille Converter - OCR Review"
        ).classes("text-h4").props(
            "id=main-heading tabindex=0"
        )

    def _build_toolbar(self):

        with ui.row().classes("items-center gap-2"):

            ui.label(
                "Open image"
            ).props("id=upload-heading")

            self.upload = ui.upload(
                label="Choose image file",
                on_upload=self.open_image,
                auto_upload=True
            ).props(
                'accept="image/*" '
                'aria-label="Choose an '
                'image file to open"'
            ).classes("max-w-[300px]")

            self.run_button = ui.button(
                "Run OCR",
                on_click=self.run_ocr
            ).props(
                'aria-label="Run OCR on '
                'the loaded image"'
            )

            self.translate_button = ui.button(
                "Translate all",
                on_click=self.translate_all
            ).props(
                'aria-label="Translate '
                'all records into '
                'Braille"'
            )

            self.export_button = ui.button(
                "Export all",
                on_click=self.export
            ).props(
                'aria-label="Export all '
                'outputs to the output '
                'folder"'
            )

    def _build_status(self):

        self.status_label = ui.label(
            "Ready"
        ).props(
            "id=app-status aria-live=polite"
        ).classes("text-body1")

    def _build_review_table(self):

        ui.label(
            "OCR Character Review"
        ).props("id=ocr-heading tabindex=0")

        columns = [
            {
                "name": "id",
                "label": "ID",
                "field": "id",
                "align": "left",
                "sortable": True
            },
            {
                "name": "text",
                "label": "TEXT",
                "field": "text",
                "align": "left",
                "sortable": True
            },
            {
                "name": "kind",
                "label": "KIND",
                "field": "kind",
                "align": "left",
                "sortable": True
            },
            {
                "name": "confidence",
                "label": "CONFIDENCE",
                "field": "confidence",
                "align": "left",
                "sortable": True
            },
            {
                "name": "approved",
                "label": "APPROVED",
                "field": "approved",
                "align": "left",
                "sortable": True
            },
            {
                "name": "box",
                "label": "BOX",
                "field": "box",
                "align": "left",
                "sortable": False
            },
            {
                "name": "braille",
                "label": "BRAILLE",
                "field": "braille",
                "align": "left",
                "sortable": False
            }
        ]

        self.table = ui.table(
            columns=columns,
            rows=[],
            row_key="id",
            selection="single"
        ).props(
            'aria-label="OCR character review results" '
            "flat bordered dense wrap-cells"
        ).classes("w-full")

        self.table.on_select(
            self.select_record
        )

    def _build_editor(self):

        with ui.card().classes("w-full").props(
            'role=group aria-label='
            '"Selected character editor"'
        ):

            ui.label(
                "Selected Character"
            ).classes("text-h6")

            # Primary, keyboard-only way to choose a
            # record. Typing filters, arrows navigate,
            # Enter selects. Clicking a table row also
            # updates this control.
            self.record_select = ui.select(
                options=[],
                label="Record ID",
                value=None,
                with_input=True,
                on_change=self.select_record_by_id
            ).props(
                'aria-label="Choose a record '
                'by its ID to edit"'
            ).classes("w-full")

            self.text_input = ui.input(
                label="OCR text",
                value=""
            ).props(
                'aria-label="OCR text '
                'of the selected '
                'character"'
            )

            self.kind_select = ui.select(
                ["literary", "math"],
                value="literary",
                label="Classification"
            ).props(
                'aria-label="Classification '
                'of the selected '
                'character"'
            )

            self.approved_checkbox = ui.checkbox(
                "Replace this OCR record",
                value=True
            ).props(
                'aria-label="Replace this '
                'OCR record with the '
                'edited values"'
            )

            self.apply_button = ui.button(
                "Apply changes",
                on_click=self.apply_edit
            ).props(
                'aria-label="Apply the '
                'edited values to the '
                'selected record"'
            )

    def _build_bounding_boxes(self):

        ui.label(
            "OCR Bounding Boxes"
        ).props("id=boxes-heading tabindex=0")

        self.boxes_card = ui.card().classes(
            "w-full min-h-[200px]"
        ).props(
            'role=group '
            'aria-label="Bounding box visualization"'
        )

        with self.boxes_card:

            self.box_summary = ui.label(
                "Run OCR to see bounding boxes."
            ).props(
                "id=box-summary aria-live=polite"
            )

            self.box_image_slot = ui.column().classes(
                "w-full items-center"
            )

            ui.label(
                "Green = approved; red = rejected."
            ).classes("text-caption")

    def _build_previews(self):

        ui.label(
            "Image Previews"
        ).props("id=previews-heading tabindex=0")

        with ui.row().classes(
            "w-full items-start gap-2"
        ):

            self.preview_card = ui.card().classes(
                "w-1/2 min-w-[220px]"
            ).props(
                'role=group '
                'aria-label="Original image preview"'
            )

            with self.preview_card:

                ui.label(
                    "Original Image Preview"
                ).props(
                    "id=preview-heading tabindex=0"
                )

                self.preview_label = ui.label(
                    "Open an image to begin"
                ).props(
                    "id=original-summary aria-live=polite"
                )

                self.preview_image_slot = ui.column().classes(
                    "w-full items-center"
                )

            self.altered_card = ui.card().classes(
                "w-1/2 min-w-[220px]"
            ).props(
                'role=group '
                'aria-label="Altered image preview"'
            )

            with self.altered_card:

                ui.label(
                    "Altered Image Preview"
                ).props(
                    "id=altered-heading tabindex=0"
                )

                self.altered_label = ui.label(
                    "Run OCR to create the "
                    "altered image."
                ).props(
                    "id=altered-summary aria-live=polite"
                )

                self.altered_image_slot = ui.column().classes(
                    "w-full items-center"
                )

    def _build_settings(self):

        with ui.card().classes("w-full").props(
            'role=group '
            'aria-label="Output settings"'
        ):

            ui.label(
                "Output Settings"
            ).classes("text-h6")

            self.layout_select = ui.select(
                list(LAYOUTS.keys()),
                value="Full page (8 × 10.5 in)",
                label="Page layout",
                on_change=self.layout_changed
            ).props(
                'aria-label="Page layout '
                'for the exported '
                'outputs"'
            )

            self.output_input = ui.input(
                label="Output folder",
                value=str(
                    Path.home() / "BrailleOutput"
                )
            ).props(
                'aria-label="Output folder '
                'for the exported files"'
            ).classes("w-full")

            ui.label(
                "Braille geometry: 1.5 mm dots, "
                "2.3 mm horizontal pitch, "
                "2.5 mm vertical pitch, "
                "6.2 mm cell pitch."
            ).classes("text-caption")

    def _build_error_dialog(self):

        self.error_dialog = ui.dialog().props(
            "persistent"
        )

        with self.error_dialog, ui.card().props(
            "role=alert"
        ).classes("min-w-[400px]"):

            self.error_title = ui.label(
                "Error"
            ).classes("text-h6")

            self.error_message = ui.label(
                ""
            ).props(
                "aria-live=assertive"
            ).classes("text-body1 whitespace-pre-wrap")

            ui.button(
                "Close",
                on_click=self._close_error
            ).props(
                'autofocus '
                'aria-label="Close the '
                'error dialog"'
            )

    # ---------------------------------------------------------
    # Startup validation. No silent failures.
    # ---------------------------------------------------------

    def _validate_startup(self):

        # The same checks power `braille-converter doctor`,
        # so the GUI and CLI cannot disagree about setup.
        problems = [
            result.detail
            for result in run_checks()
            if not result.ok
        ]

        if problems:
            self.show_error(
                "Startup problems detected",
                "\n\n".join(problems)
            )

            return

        self.status_label.set_text(
            "Ready. Environment checks passed: "
            "Tesseract and Liblouis are available."
        )

    # ---------------------------------------------------------
    # Error dialog handling.
    # ---------------------------------------------------------

    def show_error(self, title, message, source=None):

        self._error_source = source

        self.error_title.set_text(title)

        self.error_message.set_text(message)

        self.status_label.set_text(
            f"{title}: {message}"
        )

        ui.notify(
            title,
            type="negative",
            close_button="Dismiss"
        )

        self.error_dialog.open()

    def _close_error(self):

        self.error_dialog.close()

        if self._error_source is not None:

            try:
                self._error_source.run_method(
                    "focus"
                )

            except Exception:
                pass

            self._error_source = None

    # ---------------------------------------------------------
    # Long-running work.
    # ---------------------------------------------------------

    def _set_busy(self, busy):

        """Freeze the workflow while work runs off-loop.

        The status label is an aria-live region, so setting
        it before starting a job announces that the app is
        working instead of appearing to hang.
        """

        controls = (
            self.upload,
            self.run_button,
            self.translate_button,
            self.export_button,
            self.record_select,
            self.text_input,
            self.kind_select,
            self.approved_checkbox,
            self.apply_button,
            self.layout_select,
            self.output_input
        )

        for control in controls:

            if busy:
                control.disable()

            else:
                control.enable()

    # ---------------------------------------------------------
    # Workflow handlers.
    # ---------------------------------------------------------

    async def open_image(
        self,
        event: events.UploadEventArguments
    ):

        work_dir = None

        # NiceGUI 4 replaced `content`/`name` on upload events
        # with a single `file` object whose read() is async.
        # Keep the name outside the try block so even a failed
        # read can be reported against the real filename.
        file = event.file

        name = Path(file.name).name

        try:
            data = await file.read()

            # Validate before creating any temporary files:
            # an oversized or malformed upload is rejected
            # with an actionable dialog, never half-loaded.
            image = validate_upload(name, data)

            # One private directory per upload. Files with
            # the same name from different users or at
            # different times never overwrite each other,
            # and the previous upload is removed below.
            work_dir = Path(
                tempfile.mkdtemp(
                    prefix="braille-upload-"
                )
            )

            path = work_dir / name

            path.write_bytes(data)

        except UploadError as exc:

            if work_dir is not None:
                shutil.rmtree(
                    work_dir,
                    ignore_errors=True
                )

            self.show_error(
                "Invalid image",
                str(exc),
                source=self.run_button
            )

            return

        except Exception as exc:

            if work_dir is not None:
                shutil.rmtree(
                    work_dir,
                    ignore_errors=True
                )

            self.show_error(
                "Image load failed",
                f"Could not load "
                f"'{name}': {exc}",
                source=self.run_button
            )

            return

        previous_dir = None

        if self.image_path is not None:
            previous_dir = self.image_path.parent

        self.image_path = path

        self.records = []

        self.populate_table()

        loaded_status = (
            f"Loaded {name}: "
            f"{image.width} × {image.height}px. "
            "Run OCR to extract characters."
        )

        await self._refresh_visualizations(
            loaded_status
        )

        # Remove the previous upload only after the new
        # one loaded successfully, and only directories
        # this code created.
        if (
            previous_dir is not None
            and previous_dir != work_dir
            and previous_dir.name.startswith(
                "braille-upload-"
            )
        ):
            shutil.rmtree(
                previous_dir,
                ignore_errors=True
            )

    def _apply_visuals(self, data):
        """Replace the three previews with fresh images."""

        self.preview_image_slot.clear()

        with self.preview_image_slot:

            source, alt = data["original"]

            self.original_preview_image = ui.image(
                source
            ).props(f'alt="{alt}"')

        self.box_image_slot.clear()

        with self.box_image_slot:

            source, alt = data["boxed"]

            self.box_image = ui.image(
                source
            ).props(f'alt="{alt}"')

        self.altered_image_slot.clear()

        with self.altered_image_slot:

            source, alt = data["altered"]

            self.altered_preview_image = ui.image(
                source
            ).props(f'alt="{alt}"')

        self.preview_label.set_text(
            f"Original image preview for "
            f"{Path(self.image_path).name}."
        )

        self.box_summary.set_text(
            data["box_summary"]
        )

        self.altered_label.set_text(
            data["altered_summary"]
        )

    async def _refresh_visualizations(self, final_status):
        """Update previews with announced, off-loop work."""

        if not self.image_path:

            self.status_label.set_text(
                final_status
            )

            return

        self._set_busy(True)

        self.status_label.set_text(
            "Updating bounding boxes and image "
            "previews; please wait."
        )

        try:

            data = await run.io_bound(
                _render_visualization_data,
                self.image_path,
                list(self.records),
                LAYOUTS[self.layout_select.value],
                BrailleProfile()
            )

        except Exception as exc:

            self.show_error(
                "Preview failed",
                "Could not update the bounding boxes "
                "or altered image preview: "
                f"{exc}"
            )

            return

        finally:

            self._set_busy(False)

        self._apply_visuals(data)

        self.status_label.set_text(
            final_status
        )

    async def layout_changed(self, event=None):
        """Keep the altered preview in step with layout."""

        if not self.image_path:

            return

        await self._refresh_visualizations(
            "Page layout changed. The altered image "
            "preview has been updated."
        )

    async def run_ocr(self):

        if not self.image_path:
            self.show_error(
                "No image",
                "Open an image first.",
                source=self.run_button
            )

            return

        self._set_busy(True)

        self.status_label.set_text(
            "OCR running. The image is being "
            "analyzed; please wait."
        )

        try:
            self.records = await run.io_bound(
                recognize_characters,
                self.image_path
            )

        except Exception as exc:
            self.show_error(
                "OCR failed",
                f"{exc}\n\n"
                "Check that Tesseract is "
                "installed and that "
                "TESSERACT_CMD points to "
                "tesseract.exe.",
                source=self.run_button
            )

            return

        finally:
            self._set_busy(False)

        self.populate_table()

        if not self.records:
            self.show_error(
                "No characters found",
                "OCR found no characters in this "
                "image. Check that the image is "
                "sharp, correctly oriented, and "
                "that English Tesseract language "
                "data is installed "
                "(tesseract-ocr-eng).",
                source=self.run_button
            )

            return

        await self._refresh_visualizations(
            f"OCR found {len(self.records)} "
            "records. Review them in the "
            "table before translation."
        )

        ui.run_javascript(
            "var heading = "
            "document.getElementById("
            "'ocr-heading'); "
            "if (heading) { heading.focus(); }"
        )

    def populate_table(self):

        rows = []

        for record in self.records:

            confidence = (
                ""
                if record.confidence is None
                else f"{record.confidence:.2f}"
            )

            box = (
                f"{record.x1},{record.y1} - "
                f"{record.x2},{record.y2}"
            )

            braille = record.braille or ""

            rows.append({
                "id": record.id,
                "text": record.text,
                "kind": record.kind,
                "confidence": confidence,
                "approved": "yes" if record.approved else "no",
                "box": box,
                "braille": braille
            })

        self.table.rows = rows

        self.table.update()

        # Keep the keyboard selector in sync with
        # the records currently on screen.
        ids = [record.id for record in self.records]

        current = self.record_select.value

        self.record_select.set_options(
            ids,
            value=(
                current if current in ids else None
            )
        )

    def _load_editor(self, record):
        """Fill the editor fields from a record."""

        self.text_input.set_value(record.text)

        self.kind_select.set_value(record.kind)

        self.approved_checkbox.set_value(
            record.approved
        )

    def select_record_by_id(self, event):
        """Keyboard selection: load the chosen record."""

        record_id = event.value

        if record_id is None:
            return

        record = next(
            (
                r for r in self.records
                if r.id == record_id
            ),
            None
        )

        if record is None:
            return

        self._load_editor(record)

        row = next(
            (
                row for row in self.table.rows
                if row["id"] == record_id
            ),
            None
        )

        if row is not None:
            self.table.set_selection([row])

        self.status_label.set_text(
            f"Editing record {record_id}: "
            f"{record.text!r}, "
            f"confidence "
            + (
                f"{record.confidence:.2f}"
                if record.confidence is not None
                else "unknown"
            )
            + "."
        )

    def select_record(self, event):

        selected = event.args.get(
            "rows",
            []
        )

        if not selected:
            return

        row = selected[0]

        record = next(
            (
                r for r in self.records
                if r.id == row["id"]
            ),
            None
        )

        if record:
            self._load_editor(record)

            self.record_select.set_value(
                record.id
            )

    def clear_group_braille(self, group_id):
        """Drop Braille that no longer matches the text.

        Braille is derived from a word group's text and
        kind, so editing any record in the group makes
        the stored string stale. Returns True when
        something was cleared.
        """

        cleared = False

        if not group_id:
            return cleared

        for record in self.records:

            if record.group_id != group_id:
                continue

            if record.braille:
                cleared = True

            record.braille = ""

        return cleared

    async def apply_edit(self):

        record_id = self.record_select.value

        if record_id is None:
            self.show_error(
                "No record selected",
                "Choose a Record ID in the "
                "editor, or select a row in the "
                "OCR Character Review table.",
                source=self.run_button
            )

            return

        edited = None

        for record in self.records:

            if record.id == record_id:

                edited = record

                break

        if edited is None:
            self.show_error(
                "Record not found",
                f"Record {record_id} is no longer "
                "in the current OCR results. "
                "Run OCR again or choose another "
                "Record ID.",
                source=self.run_button
            )

            return

        edited.text = self.text_input.value

        edited.kind = self.kind_select.value

        edited.approved = (
            self.approved_checkbox.value
        )

        stale = self.clear_group_braille(
            edited.group_id
        )

        self.populate_table()

        row = next(
            (
                row for row in self.table.rows
                if row["id"] == record_id
            ),
            None
        )

        if row is not None:
            self.table.set_selection([row])

        message = f"Updated record {record_id}."

        if stale:
            message += (
                " Braille for that word was "
                "cleared because the text "
                "changed; run 'Translate all' "
                "again before export."
            )

        await self._refresh_visualizations(
            message
        )

    async def translate_all(self):

        if not self.records:
            self.show_error(
                "No OCR",
                "Run OCR first.",
                source=self.translate_button
            )

            return

        self._set_busy(True)

        self.status_label.set_text(
            "Translation running. Converting "
            "each reviewed word to Braille; "
            "please wait."
        )

        try:

            await run.io_bound(
                translate_records,
                self.records
            )

        except TranslationError as exc:
            self.show_error(
                "Translation error",
                str(exc),
                source=self.translate_button
            )

            return

        finally:
            self._set_busy(False)

        self.populate_table()

        await self._refresh_visualizations(
            "Translation completed. Review "
            "before export. Mathematical "
            "structure still requires "
            "verification."
        )

    def export(self):

        if not self.image_path or not self.records:
            self.show_error(
                "Nothing to export",
                "Open an image and run "
                "OCR first.",
                source=self.export_button
            )

            return

        # Use the same rules as export_outputs: a word is
        # renderable only when every character is approved
        # and the group has Braille.
        readiness = export_readiness(self.records)

        if readiness["partial"]:

            self.show_error(
                "Partially approved words",
                f"{len(readiness['partial'])} word(s) "
                "have some characters approved and "
                "some not. Approve or reject every "
                "character in a word before exporting; "
                "partially approved words are never "
                "silently dropped.",
                source=self.export_button
            )

            return

        if readiness["untranslated"]:

            self.show_error(
                "Untranslated records",
                f"{len(readiness['untranslated'])} approved "
                "word(s) have not been translated. "
                "Run 'Translate all' before "
                "exporting.",
                source=self.export_button
            )

            return

        try:
            layout = LAYOUTS[
                self.layout_select.value
            ]

            paths = export_outputs(
                self.image_path,
                self.records,
                self.output_input.value,
                layout,
                BrailleProfile()
            )

        except Exception as exc:
            self.show_error(
                "Export failed",
                f"Could not write outputs to "
                f"'{self.output_input.value}': "
                f"{exc}",
                source=self.export_button
            )

            return

        status = (
            "Export completed. Created: "
            + ", ".join(
                str(path) for path in paths
            )
        )

        skipped = len(readiness["skipped"])

        if skipped:

            status += (
                f" {skipped} word(s) were excluded "
                "because no character was approved."
            )

        self.status_label.set_text(status)

        ui.notify(
            "Export completed.",
            type="positive",
            close_button="Dismiss"
        )


@ui.page("/")
def converter_page():

    ConverterApp()
