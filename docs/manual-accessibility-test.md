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
- One stacked-fraction exemplar, such as
  `00a0b3a0485d8e735df9cb73dbdf36d6_img.jpg`, to exercise region
  proposals and fraction normalization.
- `OCR_REGION_DETECTION` left at its default (`1`) unless you are
  explicitly comparing the whole-image-only fallback.

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
      approved, origin).
- [ ] The "OCR Bounding Boxes" heading immediately to the right is
      reachable. Its live summary states the record count, the number
      of candidate regions awaiting review, the green/red/amber
      convention, and coordinates for the first records.
- [ ] The bounding-box image announces alt text naming the source
      image and summarizing the same OCR and candidate counts; it is
      not a silent graphic. Amber candidate boxes are described as
      review aids, not accepted text.
- [ ] On the stacked-fraction exemplar, normalized tokens such as
      `1/4` and `6/4` appear in the review table, while any region
      OCR did not accept remains amber only. Compare each candidate
      with the image before approving, correcting, or ignoring it.
      The supplied `/2 or 6/4` line is preserved exactly, including
      its missing numerator.
- [ ] The "Original Image Preview" and "Altered Image Preview"
      headings are reachable in that left-to-right order, and each
      image announces descriptive alt text.
- [ ] The altered preview's live summary names how many translated
      words are overlaid and warns about untranslated or mixed-
      approval words.
- [ ] Visually inspect the altered preview and exported tactile SVG:
      Braille words do not overlap. A long line wraps to a new row,
      an overlong word continues on the next row, and later source
      lines move down or rows pack tighter instead of being covered.
      The tactile SVG uses the same word positions as the PNG/PDF.
- [ ] Preview refresh announces "Updating bounding boxes and image
      previews; please wait." and disables workflow controls until
      it finishes.
- [ ] The Record ID field can be typed into; typing filters options,
      Up/Down move through them, and Enter loads the record.
- [ ] Loading a record announces "Editing record <id>: <text>,
      confidence <value>."
- [ ] The "Reject bounding box" button is announced with its name.
      Activating it announces "Rejected bounding box for record
      <id>", changes the button name to "Restore bounding box",
      and adds that record to the red/rejected count in the box
      summary. Activating it again restores the green box.
- [ ] The four "Manual box" number fields and "Add manual box"
      button are announced with their names. Typing coordinates
      and activating the button announces "Added manual box ..."
      and selects the new record for editing. A duplicate box
      opens an error dialog. Dragging on the bounding-box preview
      announces the selected coordinates and fills the four
      fields; the fields remain the authoritative way to create
      the box.
- [ ] The "Provisional region review" group and "Candidate region"
      selector are announced. Each option names its amber box as
      `C<n>: x1,y1 to x2,y2`. Activating "Accept provisional box"
      with no choice opens a "No provisional region" dialog.
      Accepting a choice announces "Accepted provisional region C1
      as record <id> ...", selects that record, removes the amber
      option from the list, and adds an accepted provisional to the
      box summary. The record's origin is `candidate` in the table.
- [ ] Translating before typing text in a new manual or provisional
      box opens a "Text required" dialog naming the record ID.
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
- Amber regions are OpenCV proposals, not human-verified text or
  accuracy ground truth. Generated fixtures in `tests/test_files/
  expected/` are regression baselines marked "human review pending";
  the supplied transcriptions in `tests/test_files/ground_truth/`
  are separate.
- Numeric fractions are normalized to slashes for literary UEB
  translation. Confirm the digits, bar, and resulting Braille cells
  against the image and the intended embosser before production.
- Tactile output must be validated on the intended embosser.
- Automated GUI tests in `tests/test_gui.py` cover labels, dialogs,
  status text, and the workflow, but not screen-reader speech.
