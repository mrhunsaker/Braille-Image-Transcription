
from pathlib import Path

import tkinter as tk

from tkinter import (
    ttk,
    filedialog,
    messagebox
)

from PIL import Image, ImageTk

from .ocr_engine import recognize_characters

from .translator import (
    translate_ueb,
    TranslationError
)

from .layout import LAYOUTS

from .braille_render import BrailleProfile

from .image_pipeline import export_outputs


class ConverterApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Braille Converter - OCR Review"
        )

        self.root.geometry("1180x760")

        self.image_path = None

        self.records = []

        self.preview_image = None

        self._build()

    def _build(self):

        toolbar = ttk.Frame(
            self.root,
            padding=8
        )

        toolbar.pack(fill="x")

        ttk.Button(
            toolbar,
            text="Open image",
            command=self.open_image
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="Run OCR",
            command=self.run_ocr
        ).pack(side="left", padx=5)

        ttk.Button(
            toolbar,
            text="Translate all",
            command=self.translate_all
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="Export all",
            command=self.export
        ).pack(side="left", padx=5)

        main = ttk.Panedwindow(
            self.root,
            orient="horizontal"
        )

        main.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8
        )

        left = ttk.Frame(main)

        right = ttk.Frame(main)

        main.add(left, weight=1)

        main.add(right, weight=2)

        # OCR review table.
        ttk.Label(
            left,
            text="OCR Character Review"
        ).pack(anchor="w")

        columns = (
            "id",
            "text",
            "kind",
            "confidence",
            "approved",
            "box"
        )

        self.tree = ttk.Treeview(
            left,
            columns=columns,
            show="headings",
            height=24
        )

        column_widths = {
            "id": 40,
            "text": 55,
            "kind": 75,
            "confidence": 80,
            "approved": 70,
            "box": 180
        }

        for column in columns:

            self.tree.heading(
                column,
                text=column.upper()
            )

            self.tree.column(
                column,
                width=column_widths[column]
            )

        self.tree.pack(
            fill="both",
            expand=True
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_record
        )

        # Editing controls.
        editor = ttk.LabelFrame(
            left,
            text="Selected Character",
            padding=8
        )

        editor.pack(
            fill="x",
            pady=8
        )

        ttk.Label(
            editor,
            text="OCR text"
        ).grid(row=0, column=0, sticky="w")

        self.text_var = tk.StringVar()

        ttk.Entry(
            editor,
            textvariable=self.text_var,
            width=15
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(
            editor,
            text="Classification"
        ).grid(row=1, column=0, sticky="w")

        self.kind_var = tk.StringVar(
            value="literary"
        )

        ttk.Combobox(
            editor,
            textvariable=self.kind_var,
            values=[
                "literary",
                "math"
            ],
            state="readonly",
            width=12
        ).grid(row=1, column=1, sticky="w")

        self.approved_var = tk.BooleanVar(
            value=True
        )

        ttk.Checkbutton(
            editor,
            text="Replace this OCR record",
            variable=self.approved_var
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w"
        )

        ttk.Button(
            editor,
            text="Apply changes",
            command=self.apply_edit
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            pady=5
        )

        # Right side preview.
        ttk.Label(
            right,
            text="Original Image Preview"
        ).pack(anchor="w")

        self.preview = ttk.Label(
            right,
            text="Open an image to begin",
            anchor="center"
        )

        self.preview.pack(
            fill="both",
            expand=True
        )

        # Output settings.
        settings = ttk.LabelFrame(
            right,
            text="Output Settings",
            padding=8
        )

        settings.pack(fill="x")

        ttk.Label(
            settings,
            text="Page layout"
        ).grid(row=0, column=0, sticky="w")

        self.layout_var = tk.StringVar(
            value="Full page (8 × 10.5 in)"
        )

        ttk.Combobox(
            settings,
            textvariable=self.layout_var,
            values=list(LAYOUTS.keys()),
            state="readonly",
            width=28
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(
            settings,
            text="Output folder"
        ).grid(row=1, column=0, sticky="w")

        self.output_var = tk.StringVar(
            value=str(
                Path.home() / "BrailleOutput"
            )
        )

        ttk.Entry(
            settings,
            textvariable=self.output_var,
            width=40
        ).grid(row=1, column=1, sticky="ew")

        ttk.Button(
            settings,
            text="Browse",
            command=self.choose_output
        ).grid(row=1, column=2, padx=4)

        settings.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            settings,
            text=(
                "Braille geometry: 1.5 mm dots, "
                "2.3 mm horizontal pitch, "
                "2.5 mm vertical pitch, "
                "6.2 mm cell pitch."
            )
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            pady=6
        )

        self.status = tk.StringVar(
            value="Ready"
        )

        ttk.Label(
            self.root,
            textvariable=self.status,
            relief="sunken",
            anchor="w"
        ).pack(fill="x")

    def open_image(self):

        path = filedialog.askopenfilename(
            filetypes=[
                (
                    "Raster images",
                    "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"
                ),
                (
                    "All files",
                    "*.*"
                )
            ]
        )

        if not path:
            return

        try:

            image = Image.open(
                path
            ).convert("RGB")

        except Exception as exc:

            messagebox.showerror(
                "Image error",
                str(exc)
            )

            return

        self.image_path = Path(path)

        self.records = []

        self.populate_tree()

        self.show_preview(image)

        self.status.set(
            f"Loaded {self.image_path.name}: "
            f"{image.width} × {image.height}px"
        )

    def show_preview(self, image):

        preview = image.copy()

        preview.thumbnail(
            (760, 590)
        )

        self.preview_image = ImageTk.PhotoImage(
            preview
        )

        self.preview.configure(
            image=self.preview_image,
            text=""
        )

    def run_ocr(self):

        if not self.image_path:

            messagebox.showinfo(
                "Open image",
                "Choose an image first."
            )

            return

        try:

            self.records = recognize_characters(
                self.image_path
            )

            self.populate_tree()

            self.status.set(
                f"OCR found {len(self.records)} records."
                " Review them before translation."
            )

        except Exception as exc:

            messagebox.showerror(
                "OCR failed",
                f"{exc}\n\n"
                "Check that Tesseract is installed."
            )

    def populate_tree(self):

        self.tree.delete(
            *self.tree.get_children()
        )

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

            self.tree.insert(
                "",
                "end",
                iid=str(record.id),
                values=(
                    record.id,
                    record.text,
                    record.kind,
                    confidence,
                    record.approved,
                    box
                )
            )

    def select_record(self, event=None):

        selected = self.tree.selection()

        if not selected:
            return

        record_id = int(selected[0])

        record = next(
            (
                r for r in self.records
                if r.id == record_id
            ),
            None
        )

        if record:

            self.text_var.set(
                record.text
            )

            self.kind_var.set(
                record.kind
            )

            self.approved_var.set(
                record.approved
            )

    def apply_edit(self):

        selected = self.tree.selection()

        if not selected:
            return

        record_id = int(selected[0])

        for record in self.records:

            if record.id == record_id:

                record.text = self.text_var.get()

                record.kind = self.kind_var.get()

                record.approved = self.approved_var.get()

                break

        self.populate_tree()

        self.tree.selection_set(
            str(record_id)
        )

    def translate_all(self):

        if not self.records:

            messagebox.showinfo(
                "No OCR",
                "Run OCR first."
            )

            return

        # Group characters into OCR words.
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

                # Reconstruct the corrected token.
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

                # Store the complete token translation
                # on its first character record.
                for index, record in enumerate(group):

                    record.braille = (
                        translated if index == 0 else ""
                    )

            self.populate_tree()

            self.status.set(
                "Translation completed. Review before export."
            )

            messagebox.showinfo(
                "Translation complete",
                "Translation completed.\n\n"
                "Mathematical structure still requires verification."
            )

        except TranslationError as exc:

            messagebox.showerror(
                "Translation error",
                str(exc)
            )

    def choose_output(self):

        folder = filedialog.askdirectory()

        if folder:

            self.output_var.set(
                folder
            )

    def export(self):

        if not self.image_path or not self.records:

            messagebox.showinfo(
                "Nothing to export",
                "Open an image and run OCR first."
            )

            return

        if any(
            not record.braille
            for record in self.records
            if record.approved
        ):

            proceed = messagebox.askyesno(
                "Untranslated records",
                "Some records have not been translated. "
                "Export anyway?"
            )

            if not proceed:
                return

        try:

            layout = LAYOUTS[
                self.layout_var.get()
            ]

            paths = export_outputs(
                self.image_path,
                self.records,
                self.output_var.get(),
                layout,
                BrailleProfile()
            )

            messagebox.showinfo(
                "Export complete",
                "Created:\n\n"
                + "\n".join(
                    str(path) for path in paths
                )
            )

            self.status.set(
                "Export completed."
            )

        except Exception as exc:

            messagebox.showerror(
                "Export failed",
                str(exc)
            )
