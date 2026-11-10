# Contributing to Braille Converter

Thank you for your interest in contributing! This project
converts raster images of text and mathematics into Unified
English Braille, and it is built to be usable by blind and
low-vision users with screen readers. Please keep
accessibility in mind with every change.

## Getting started

1. Clone the repository.

2. Install Python 3.11+ and [uv](https://docs.astral.sh/uv/).

3. Install the dependencies:

       uv sync --extra dev

4. Install the external tools:

   - Tesseract OCR (Windows:
     `winget install -e --id UB-Mannheim.TesseractOCR`)
   - Liblouis with UEB tables

   See README.md for details and configuration options.

5. Run the test suite:

       uv run pytest

   Tests that need Tesseract or Liblouis skip with a clear
   reason when the tools are missing.

## Development workflow

- Follow CODE_STYLE.md.
- Record every user-visible change in CHANGES.md (Keep a
  Changelog format) in the same commit as the change.
- Commit in small, complete steps with imperative subject
  lines (`Add …`, `Fix …`, `Refactor …`).
- Push your branch and open a pull request describing what
  changed and why.

## Accessibility requirements

- The GUI must remain fully operable by keyboard alone and
  must work with NVDA and JAWS on Windows.
- Every control needs a label; status changes must be
  announced through an aria-live region.
- Errors must never fail silently; they must surface in an
  accessible dialog with actionable text.

## Reporting bugs

Open an issue using the bug report template. Include the
image you processed (if you can share it), the exact steps,
and any error dialog text.

## Submitting pull requests

- Keep pull requests focused on one topic.
- Update CHANGES.md as part of your change.
- Make sure `uv run pytest` passes.
