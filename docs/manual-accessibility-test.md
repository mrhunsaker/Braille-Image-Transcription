# Manual accessibility test

Automated tests can prove that labels, roles, the aria-live region,
and the error dialog exist. They cannot prove what NVDA or JAWS
actually announces, or whether a keyboard-only user can complete the
workflow. This checklist is the manual pass. Run it before a release
that touches `src/braille_converter/gui.py`.

Record the result in the release pull request: operating system,
screen reader and version, browser, and any step that failed.

## Environment

- Windows 10 or 11, display scaling 100% or 150%.
- NVDA (latest stable) or JAWS (current version).
- A browser started from the keyboard (Chrome, Edge, or Firefox).
- Tesseract and Liblouis installed, so startup passes its checks.
- One worksheet image from `tests/test_files/`.

Run the checklist twice: once in browser mode
(`uv run braille-converter`) and, if the native extra is installed
(`uv sync --extra native`), once with `--native` or
`BRAILLE_CONVERTER_NATIVE=1`.

## Startup

- [ ] After the page loads, the status region announces
      "Ready. Environment checks passed: Tesseract and Liblouis are
      available."
- [ ] With a broken environment (for example, set
      `TESSERACT_CMD=C:\missing.exe`), the error dialog opens by
      itself and is announced as an alert.
- [ ] The dialog's Close button has focus; Enter closes it.
- [ ] The dialog text names the missing tool and how to fix it.

## Keyboard-only workflow

Use only Tab, Shift+Tab, arrows, Enter, and Space.

- [ ] The first Tab reaches the "Choose image file" uploader and its
      name is announced, not just "button".
- [ ] Run OCR, Translate all, and Export all are reachable and their
      names are announced.
- [ ] Choosing an image announces "Loaded <file name>: <width> by
      <height> pixels. Run OCR to extract characters."
- [ ] Activating Run OCR announces the record count and moves focus to
      the "OCR Character Review" heading.
- [ ] The review table announces its accessible name and column
      headers (ID, text, classification, confidence, Braille,
      approved).
- [ ] The Record ID field can be typed into; typing filters options,
      Up/Down move through them, and Enter loads the record.
- [ ] Loading a record announces "Editing record <id>: <text>,
      confidence <value>."
- [ ] Editing OCR text and classification, then activating Apply
      changes, announces "Updated record <id>." and, when the word had
      Braille, that the Braille was cleared.
- [ ] Exporting before translating announces that approved words are
      untranslated and names how many.
- [ ] Translate all announces completion and the caution about
      mathematical structure.
- [ ] Setting an invalid output folder and exporting announces the
      failure with the folder path.
- [ ] A successful export announces "Export completed. Created: ..."
      with every written path, and the toast is short enough to be
      read without losing the dialog.

## Focus and error handling

- [ ] Closing every error dialog returns focus to the control that
      failed (Run OCR, Translate all, or Export all).
- [ ] Status changes are spoken without moving focus.
- [ ] No error appears only as a toast; the dialog and status region
      always contain the full text.
- [ ] Tab never moves into a hidden or disabled control, and no
      keyboard trap exists.

## Native window (optional)

- [ ] `--native` opens a desktop window instead of a browser tab.
- [ ] All checks above pass in that window.
- [ ] Closing the window ends the process without a traceback.

## Known limits

- Braille correctness is a separate check; this document covers
  reaching and operating the controls, not the quality of the
  translation.
- Tactile output must be validated on the intended embosser.
- Automated GUI tests in `tests/test_gui.py` cover labels, dialogs,
  status text, and the workflow, but not screen-reader speech.
