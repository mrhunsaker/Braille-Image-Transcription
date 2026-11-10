
from pathlib import Path
import base64
import io
import tempfile

from nicegui import events, ui

from PIL import Image

import pytesseract

from .ocr_engine import (
    configure_tesseract,
    recognize_characters
)

from .translator import (
    find_lou_translate,
    load_env_file,
    translate_ueb,
    TranslationError
)

from .layout import LAYOUTS

from .braille_render import BrailleProfile

from .image_pipeline import export_outputs


UPLOAD_DIR = Path(
    tempfile.gettempdir()
) / "braille_converter"


def tesseract_problems():
    """Return a list of Tesseract startup problems."""

    problems = []

    try:
        configure_tesseract()

        pytesseract.get_tesseract_version()

    except Exception as exc:
        problems.append(
            f"Tesseract OCR is not available: {exc}. "
            "Install Tesseract (for example with "
            "'winget install -e --id "
            "UB-Mannheim.TesseractOCR'), make sure "
            "tesseract.exe is on PATH, or set the "
            "TESSERACT_CMD environment variable to "
            "its full path."
        )

    return problems


def liblouis_problems():
    """Return a list of Liblouis startup problems."""

    problems = []

    try:
        load_env_file()

    except TranslationError as exc:
        problems.append(str(exc))

    try:
        translated = translate_ueb("a")

        if not translated:
            problems.append(
                "Liblouis returned an empty "
                "translation for a test word."
            )

    except TranslationError as exc:
        problems.append(str(exc))

    return problems


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

            with ui.row().classes("w-full items-start"):

                with ui.column().classes("w-1/2 min-w-[500px]"):

                    self._build_review_table()

                    self._build_editor()

                with ui.column().classes("w-1/2 min-w-[400px]"):

                    self._build_preview()

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
                on_upload=self.open_image,
                auto_upload=True
            ).props(
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
            row_key="id"
        ).props(
            "selection=single flat bordered "
            "dense wrap-cells"
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

            ui.button(
                "Apply changes",
                on_click=self.apply_edit
            ).props(
                'aria-label="Apply the '
                'edited values to the '
                'selected record"'
            )

    def _build_preview(self):

        ui.label(
            "Original Image Preview"
        ).props("id=preview-heading tabindex=0")

        self.preview_card = ui.card().classes(
            "w-full min-h-[200px]"
        )

        with self.preview_card:

            self.preview_label = ui.label(
                "Open an image to begin"
            ).props("aria-live=polite")

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
                label="Page layout"
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

        problems = []

        problems.extend(tesseract_problems())

        problems.extend(liblouis_problems())

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
            f"{title}: {message}",
            type="negative",
            close_button="Dismiss",
            multiline=True
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
    # Workflow handlers.
    # ---------------------------------------------------------

    def open_image(self, event: events.UploadEventArguments):

        try:
            data = event.content.read()

            if not data:
                raise ValueError(
                    "The selected file is empty."
                )

            name = Path(event.name).name

            UPLOAD_DIR.mkdir(
                parents=True,
                exist_ok=True
            )

            path = UPLOAD_DIR / name

            path.write_bytes(data)

            image = Image.open(path).convert("RGB")

        except Exception as exc:
            self.show_error(
                "Image load failed",
                f"Could not load "
                f"'{event.name}': {exc}",
                source=self.run_button
            )

            return

        self.image_path = path

        self.records = []

        self.populate_table()

        self._show_preview(image)

        self.status_label.set_text(
            f"Loaded {name}: "
            f"{image.width} × {image.height}px. "
            "Run OCR to extract characters."
        )

    def _show_preview(self, image):

        preview = image.copy()

        preview.thumbnail((760, 590))

        buffer = io.BytesIO()

        preview.save(buffer, format="PNG")

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode("ascii")

        alt = (
            f"Preview of "
            f"{self.image_path.name}, "
            f"{image.width} by "
            f"{image.height} pixels."
        ).replace('"', "'")

        with self.preview_card:

            self.preview_card.clear()

            ui.image(
                src=(
                    f"data:image/png;base64,"
                    f"{encoded}"
                )
            ).props(f'alt="{alt}"')

    def run_ocr(self):

        if not self.image_path:
            self.show_error(
                "No image",
                "Open an image first.",
                source=self.run_button
            )

            return

        try:
            self.records = (
                recognize_characters(
                    self.image_path
                )
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

        self.populate_table()

        self.status_label.set_text(
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
            self.text_input.set_value(
                record.text
            )

            self.kind_select.set_value(
                record.kind
            )

            self.approved_checkbox.set_value(
                record.approved
            )

    def apply_edit(self):

        selected = self.table.selected

        if not selected:
            self.show_error(
                "No record selected",
                "Select a row in the OCR "
                "Character Review table first.",
                source=self.run_button
            )

            return

        record_id = selected[0]["id"]

        for record in self.records:

            if record.id == record_id:

                record.text = (
                    self.text_input.value
                )

                record.kind = (
                    self.kind_select.value
                )

                record.approved = (
                    self.approved_checkbox.value
                )

                break

        self.populate_table()

        self.table.set_selection(
            [selected[0]]
        )

        self.status_label.set_text(
            f"Updated record {record_id}."
        )

    def translate_all(self):

        if not self.records:
            self.show_error(
                "No OCR",
                "Run OCR first.",
                source=self.translate_button
            )

            return

        groups = {}

        for record in self.records:

            groups.setdefault(
                record.group_id,
                []
            ).append(record)

        try:

            for group in groups.values():

                group.sort(
                    key=lambda r: r.x1
                )

                token = "".join(
                    r.text for r in group
                )

                math_mode = any(
                    r.kind == "math"
                    for r in group
                )

                translated = translate_ueb(
                    token,
                    math_mode=math_mode
                )

                if not translated:
                    raise TranslationError(
                        f"Liblouis returned an empty "
                        f"translation for token "
                        f"{token!r}."
                    )

                for index, record in enumerate(group):

                    record.braille = (
                        translated
                        if index == 0
                        else ""
                    )

        except TranslationError as exc:
            self.show_error(
                "Translation error",
                str(exc),
                source=self.translate_button
            )

            return

        self.populate_table()

        self.status_label.set_text(
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

        if any(
            not record.braille
            for record in self.records
            if record.approved
        ):
            self.show_error(
                "Untranslated records",
                "Some approved records have "
                "not been translated. Run "
                "'Translate all' before "
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

        self.status_label.set_text(
            "Export completed. Created: "
            + ", ".join(
                str(path) for path in paths
            )
        )

        ui.notify(
            "Export completed.",
            type="positive",
            close_button="Dismiss"
        )


@ui.page("/")
def converter_page():

    ConverterApp()
