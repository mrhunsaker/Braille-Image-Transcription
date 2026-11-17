
# Braille Converter

A Python desktop application for converting raster images
containing text and mathematical notation into Braille.

## Features

- Import JPG, JPEG, PNG, TIFF, BMP, and WEBP.
- Screen-reader-accessible web GUI (NiceGUI).
- Character-level OCR using Tesseract.
- Original-image pixel coordinates.
- Accessible bounding-box visualization beside the OCR review
  column, with green approved boxes and red rejected boxes.
- Side-by-side original and altered image previews. The altered
  preview is rendered by the same pipeline as the exported PNG.
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
- `braille-converter doctor` command for checking the setup
  from a terminal.
- Full keyboard operation with screen-reader semantics (labelled
  controls, aria-live status, accessible error dialogs, and a
  keyboard-operable record selector).

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
take precedence over .env values. See `template.env` for a
commented example.

If lou_translate is not on PATH, the application also checks
the LOU_TRANSLATE_CMD environment variable and common
install locations such as C:\Liblouis\bin.

## Check your environment

Run the same checks the GUI performs on startup:

    uv run braille-converter doctor

The command prints the Tesseract version and executable, the
Liblouis tables and executable, the translation timeout, and
a sample translation. Every failed check includes a fix; the
command exits 1 when anything is wrong. No GUI or browser is
required.

## Environment variables

All settings can be placed in a `.env` file in the project root
(one `KEY=VALUE` per line) or set in the OS environment. OS
values win over `.env` values.

| Variable | Default | Purpose |
| --- | --- | --- |
| `TESSERACT_CMD` | auto-detected | Full path to `tesseract.exe` when it is not on PATH. |
| `LOU_TRANSLATE_CMD` | auto-detected | Full path to `lou_translate` when it is not on PATH. |
| `LIBLOUIS_UEB_TABLE` | `en-ueb-g2.ctb` | Literary Braille table. |
| `LIBLOUIS_UEB_MATH_TABLE` | `en-ueb-math.ctb` | Math Braille table. |
| `LIBLOUIS_TIMEOUT` | `30` | Seconds before a Liblouis translation is reported as hung. |
| `BRAILLE_CONVERTER_MAX_UPLOAD_MB` | `25` | Largest accepted image upload, in MB. |
| `BRAILLE_CONVERTER_MAX_IMAGE_DIMENSION` | `8000` | Largest accepted upload, in pixels per side. |
| `BRAILLE_CONVERTER_NATIVE` | unset | Set to `1` to open the native window instead of a browser. |

An empty or commented-out value means "use the default". Malformed
lines in `.env` are reported, never skipped silently.

## Run

    uv run braille-converter

The app starts a local web server and opens
http://localhost:8787 in your default browser.

On startup the app validates the environment (Tesseract,
Liblouis, .env) and shows a dialog listing anything missing,
with instructions for fixing it.

Optional native window mode (requires the `native` extra):

    uv sync --extra native
    uv run braille-converter --native

`set BRAILLE_CONVERTER_NATIVE=1` has the same effect.

## Command-line conversion

For batch work or scripted use, the same pipeline runs without the
GUI:

    uv run braille-converter convert worksheet.jpg --out braille_output
    uv run braille-converter convert scans/ --out braille_output --layout full
    uv run braille-converter convert equation.png --math

Each image writes the four output files listed below. The command
prints every written path, reports each failed image on stderr, and
exits 1 if any image failed (2 for a missing input path). Run
`uv run braille-converter --help` for all options.

## Using the app with a screen reader

Every control is reachable with Tab and Shift+Tab and has a
spoken label. The workflow is:

1. Tab to "Open image" and press Enter to choose a file.
2. Tab to "Run OCR" and press Enter.
3. Tab to "Record ID" in the Selected Character editor. Type part
   of an ID to filter, use the arrow keys to navigate, and press
   Enter to load the record. The editor fields and the matching
   table row update, and the status region announces the record.
   The "OCR Bounding Boxes" heading immediately to the right
   describes the matching box in its live summary.
4. Edit "OCR text" and "Classification", then activate "Apply
   changes". The bounding boxes and both previews update with
   your approval and translation state.
5. Tab to "Translate all" and press Enter.
6. Set the "Output folder" and "Page layout", then activate
   "Export all". Changing the page layout refreshes the altered
   preview.

Status changes are announced through an aria-live region, and
errors appear in a modal dialog with an autofocused Close button
(Enter dismisses it; focus returns to the control that failed).

Before a release that changes the GUI, run the
[manual accessibility test](docs/manual-accessibility-test.md) with
NVDA or JAWS and record the result in the pull request.

## Output files

The application produces:

    filename_braille.png
    filename_braille.pdf
    filename_ocr.json
    filename_tactile.svg

## Testing

    uv run pytest

The suite skips OCR tests when Tesseract is missing and translation
tests when Liblouis is missing. Exact OCR expectations are stored
per Tesseract version under `tests/test_files/expected/<version>/`;
the exact comparison runs whenever fixtures exist for the installed
version, while version-independent checks (word-count floor,
determinism, ordering and translation) always run. CI installs both
tools on Ubuntu and Tesseract on Windows, and uploads generated
fixtures for each runner's Tesseract version.

To measure coverage:

    uv run pytest --cov=braille_converter --cov-report=term-missing

Lint with:

    uv run ruff check .

## Troubleshooting

Run `uv run braille-converter doctor` first. It names the failing
check and prints the setting or install step that fixes it.

- **"Tesseract OCR is not available"** — install Tesseract with
  English language data, add its `bin` directory to PATH, or set
  `TESSERACT_CMD` to the full path of `tesseract.exe`.
- **"Liblouis was not found"** — install Liblouis with the UEB
  tables, add its `bin` directory to PATH, or set
  `LOU_TRANSLATE_CMD`. On Windows a typical path is
  `C:\Liblouis\bin\lou_translate.exe`.
- **"Braille table not found"** — the table path in
  `LIBLOUIS_UEB_TABLE` or `LIBLOUIS_UEB_MATH_TABLE` is wrong.
  Point it at the installed `.ctb` file or remove the setting to
  use the built-in table name.
- **"Liblouis timed out"** — the input or table is wedged. Check
  the table, then raise `LIBLOUIS_TIMEOUT` if translation is
  legitimately slow.
- **"Invalid image"** — the upload was rejected before OCR. The
  dialog names the file and the exact limit; resize the image or
  adjust `BRAILLE_CONVERTER_MAX_UPLOAD_MB` /
  `BRAILLE_CONVERTER_MAX_IMAGE_DIMENSION`.
- **"Partially approved words"** — every character in a word must
  be approved or rejected before export. Partially approved words
  are never silently dropped.
- **"Untranslated records"** — run "Translate all" after OCR or
  after editing any word; edits clear that word's Braille.
- **The app looks frozen** — OCR and translation run off the UI
  event loop and announce "OCR running" / "Translation running"
  in the status region. Controls are disabled until the work is
  done.
- **Exact OCR tests skip on my machine** — generate fixtures for
  the installed Tesseract version with
  `uv run python scripts/generate_expected.py` and commit the new
  `tests/test_files/expected/<version>/` directory. Generated
  fixtures are regression baselines, not human-verified ground
  truth.

## Packaging

There is no supported one-file build yet. NiceGUI applications need
a browser or the optional native window; see the NiceGUI packaging
documentation. The `convert` subcommand is the supported way to run
the pipeline unattended.

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
