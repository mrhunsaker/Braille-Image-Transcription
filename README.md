
# Braille Converter

A Python desktop application for converting raster images
containing text and mathematical notation into Braille.

## Features

- Import JPG, JPEG, PNG, TIFF, BMP, and WEBP.
- Screen-reader-accessible web GUI (NiceGUI).
- Character-level OCR using Tesseract.
- Original-image pixel coordinates.
- Human OCR correction.
- Literary and mathematical classification.
- UEB translation through Liblouis.
- Unicode Braille representation.
- Physical Braille dot rendering.
- Half-page and full-page layouts.
- PNG export.
- US Letter PDF export.
- JSON export.
- Tactile-dot SVG export.
- Startup validation with explicit error dialogs for missing
  dependencies (no silent failures).

## Requirements

- Python 3.11+
- uv
- Tesseract OCR
- Liblouis with UEB tables
- A modern web browser (the GUI runs locally and opens in your
  default browser; this gives the best screen-reader support)

## Install Python dependencies

From the project root:

    uv sync --extra dev

## Install Tesseract

Windows:

Install Tesseract OCR and add its executable to PATH.

Alternatively, define:

    TESSERACT_CMD

with the full path to tesseract.exe.

## Install Liblouis

Install Liblouis and its UEB tables.

The application uses:

    en-ueb-g2.ctb

for literary translation (contracted Unified English Braille) and:

    en-ueb-math.ctb

for mathematical translation.

Set LIBLOUIS_UEB_TABLE or LIBLOUIS_UEB_MATH_TABLE to use
different tables. A .env file in the project root with
KEY=VALUE lines is also honored; OS environment variables
take precedence over .env values.

If lou_translate is not on PATH, the application also checks
the LOU_TRANSLATE_CMD environment variable and common
install locations such as C:\Liblouis\bin.

## Run

    uv run braille-converter

The app starts a local web server and opens
http://localhost:8787 in your default browser.

On startup the app validates the environment (Tesseract,
Liblouis, .env) and shows a dialog listing anything missing,
with instructions for fixing it.

Optional native window mode (requires pywebview):

    set BRAILLE_CONVERTER_NATIVE=1
    uv run braille-converter

## Output files

The application produces:

    filename_braille.png
    filename_braille.pdf
    filename_ocr.json
    filename_tactile.svg

## Testing

    uv run pytest

## Community files

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to set up and
  submit changes
- [CODE_STYLE.md](CODE_STYLE.md) — the code style of this
  repository
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Contributor
  Covenant
- [CONTRIBUTORS.md](CONTRIBUTORS.md) — contributor list
- [SECURITY.md](SECURITY.md) — how to report vulnerabilities
- [SUPPORT.md](SUPPORT.md) — where to get help
- [CHANGES.md](CHANGES.md) — changelog

## PyInstaller

The previous tkinter-based PyInstaller instructions no longer
apply. NiceGUI applications package differently; see the
NiceGUI PyInstaller documentation for the current
recommended approach. A verified spec file for this project
has not yet been produced.

## Important limitations

This is an OCR and Braille conversion prototype.

Mathematical OCR must identify semantic relationships,
including superscripts, subscripts, fractions, and radicals.

OCR text alone cannot reliably determine these relationships.

Inpainting can damage diagrams, grid lines, and other
background features.

Visual Braille output is not tactile Braille.

The tactile SVG must be validated against the intended
embosser or tactile production system.

All mathematical transcription should be reviewed
before educational or production use.
