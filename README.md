
# Braille Converter

A Python desktop application for converting raster images
containing text and mathematical notation into Braille.

## Features

- Import JPG, JPEG, PNG, TIFF, BMP, and WEBP.
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

## Requirements

- Python 3.11+
- uv
- Tesseract OCR
- Liblouis with UEB tables

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

    en-ueb-g1.ctb

for literary translation and:

    en-ueb-math.ctb

for mathematical translation.

Set LIBLOUIS_TABLES if the table directory is
not automatically detected by your installation.

The environment variables:

    LIBLOUIS_UEB_TABLE
    LIBLOUIS_UEB_MATH_TABLE

can be used to specify table paths.

## Run

    uv run braille-converter

## Output files

The application produces:

    filename_braille.png
    filename_braille.pdf
    filename_ocr.json
    filename_tactile.svg

## Testing

    uv run pytest

## PyInstaller

Build the Windows application on Windows:

    uv run pyinstaller --noconfirm --clean --onedir --windowed --name BrailleConverter --collect-all pytesseract --collect-all PIL -m braille_converter.main

For a more reliable build, use a PyInstaller spec file
and explicitly configure external Tesseract and
Liblouis executables and their data files.

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
