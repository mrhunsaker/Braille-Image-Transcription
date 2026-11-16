# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- tests/test_gui.py: GUI test suite driving the real NiceGUI app in
  NiceGUI's user simulation. Covers page rendering, startup status
  reporting, the no-image and nothing-to-export error dialogs, the
  no-record-selected dialog, export blocking before translation, the
  full workflow (load image, run OCR, translate, export) asserting all
  four output formats are written, and keyboard record selection
  driving the editor and table. Eight tests.
- pytest-asyncio dev dependency and pytest configuration
  (asyncio_mode = auto) so the GUI simulation tests can run.
- End-to-end verification of the export pipeline: all four artifacts
  (PNG, PDF, JSON, tactile SVG) were produced from a test image and
  checked numerically (non-blank PNG, SVG dot circles, valid JSON
  records, PDF header).
- template.env (committed through the git index during task 3):
  a tracked template for the git-ignored .env file. The values are
  blank so the template is safe to commit; LIBLOUIS_NEMETH_TABLE is
  listed in the template but is not read by the current code.
- Community and repository files for GitHub: CONTRIBUTORS.md,
  CONTRIBUTING.md, CODE_STYLE.md (codifying the actual style of
  this codebase), CODE_OF_CONDUCT.md (Contributor Covenant
  2.1), SECURITY.md, SUPPORT.md, issue templates (bug report,
  feature request), a pull request template with accessibility
  checkboxes, and a CI workflow (GitHub Actions, uv + pytest
  with Liblouis installed; Tesseract-dependent tests skip in
  CI because expected OCR data is Tesseract-version specific).
- README.md links to all community files.
- CHANGES.md changelog (Keep a Changelog 1.1 format). Every change is
  recorded here at the time it is made.
- prompt.json work order describing the NiceGUI migration, pipeline
  optimization, accessibility requirements, error-handling policy, and
  repository files for GitHub.
- nicegui dependency for the screen-reader-accessible web GUI.
- uv.lock is now tracked. uv recommends committing the lockfile for
  applications so environments are reproducible.
- .env loading (dependency-free). Values are applied at startup;
  existing OS environment variables take precedence. Malformed lines
  (missing '=' or empty key) raise TranslationError with the line
  number and file path instead of being skipped silently.
- lou_translate discovery now checks, in order: the LOU_TRANSLATE_CMD
  environment variable, the system PATH, and common install locations
  (including C:\Liblouis\bin on Windows). When nothing is found,
  TranslationError lists every location checked and how to fix it.
- Table existence checking: absolute table paths that do not exist
  raise TranslationError before any subprocess runs.
- tests/test_translator.py covering g2 translation, .env loading,
  malformed .env rejection, missing-table errors, and empty input.
  Liblouis-dependent tests skip with a clear reason when Liblouis is
  unavailable.
- NiceGUI web GUI (gui.py) replacing the tkinter GUI, rebuilt around
  the same workflow and the same underlying pipeline functions
  (recognize_characters, translate_ueb, export_outputs). The app opens
  in the default browser for best screen-reader compatibility; set
  BRAILLE_CONVERTER_NATIVE=1 to try native-window mode (requires
  pywebview).
- Accessible OCR review table (ui.table) with sortable, labelled
  columns for id, text, kind, confidence, approved, box, and braille,
  plus an aria-label naming the table.
- Keyboard-only record selection: a "Record ID" select (typed
  filtering, arrow navigation, Enter) in the Selected Character editor
  is the primary way to choose a record; choosing an ID loads the
  editor, highlights the matching table row, and announces the record
  and its confidence in the status region. Clicking a table row also
  updates this control, so mouse and keyboard stay in sync. The
  Quasar data table's own row selection is not reliably reachable by
  keyboard, which is why this control exists.
- Modal error dialog for every failure (image load, OCR, translation,
  export, startup validation): role=alert, aria-live=assertive
  message, autofocus Close button (Enter), Escape to dismiss, and
  focus returned to the invoking control on close. Status changes and
  errors are mirrored in an aria-live=polite region and in
  notifications.
- Startup validation runs on page build and opens the error dialog
  listing missing Tesseract or Liblouis problems (with remediation
  text) before any work is attempted.
- Focus management: after OCR completes focus moves to the results
  table heading; main headings are focusable landmarks.
- Image preview carries meaningful alt text (filename and pixel
  dimensions).
- Output folder is a labelled text input (typed path) rather than a
  mouse-only folder picker.
- Verified end to end: the app serves HTTP 200 with the startup
  validation dialog on a machine without Tesseract, and with
  TESSERACT_CMD pointed at a nonexistent path the dialog echoes the
  bad path with remediation text (role=alert, aria-live=assertive).
- scripts/benchmark.py measures per-image pipeline metrics (records,
  words, mean confidence, translated words) over tests/test_files.
  It exits non-zero when any image fails to process. The baseline
  (tests/test_files/benchmark_baseline.txt, Tesseract 5.4.0):
  one image returns 0 records (6d6670b8, 359x216 px) and one has
  0.0 mean confidence (9df11121) because no characters could be
  associated with detected words.
- OCR now uses --psm 6 (uniform block of text) for both word and
  character detection. Measured over all 7 test images, psm 6
  detects 136 words vs 41 for the previous psm 11; see
  tests/test_files/benchmark_report.md for the full comparison of
  psm modes and preprocessing variants (upscaling and
  autocontrast measured worse and are rejected).
- ocr_engine.py word/character association replaced the O(n*m)
  linear scan with a bucketed grid index, and records are now
  ordered stably by word (top-to-bottom, left-to-right reading
  order) then horizontal position.
- Fixed the root cause of the 9df11121 zero-confidence result:
  word detection used psm 11 while character detection used the
  default psm 3, so their boxes came from different
  segmentations and no character ever matched a word. Both calls
  now use the same psm so the segmentations agree.
- OCR results after the changes (full report and trade-off
  discussion in tests/test_files/benchmark_report.md):
  6d6670b8 0 -> 5 records, 9df11121 confidence 0.0 -> 0.763,
  and more real content detected on every image.
- scripts/generate_expected.py regenerates the expected OCR
  results in tests/test_files/expected/<stem>.json (word lists,
  record and word counts). The files are marked
  generated-and-human-review-pending.
- tests/test_pipeline.py integration suite running the real
  pipeline over all 7 test images: record/group counts match
  the expected data, group characters are left-to-right
  ordered, tokens are non-empty, every detected word
  translates, and .env stays valid. Tesseract- and
  Liblouis-dependent tests skip with clear reasons when the
  tools are absent.
- Automatic literary/math classification hint: records from a
  word containing math symbols (for example =, +, (, ), ×) are
  initially classified as math; everything else as literary.
  The reviewer can still change the classification of any
  record.
- CI now installs Tesseract (tesseract-ocr, tesseract-ocr-eng)
  as well as Liblouis, so OCR tests actually run instead of
  being skipped. The workflow also pins uv to the committed
  lockfile (uv sync --frozen), caches uv downloads, prints
  tool versions, limits job permissions to read-only, cancels
  superseded runs, and has a 20-minute timeout.
- Expected OCR data now records the Tesseract version and a
  min_word_count floor. The exact record/word-count test runs
  only when the installed Tesseract matches the recorded
  version (counts are version specific); the floor test and
  the other checks run on any version, so a catastrophic OCR
  regression still fails CI.
- Version-independent pipeline tests: deterministic output
  (same image processed twice gives identical records) and a
  minimum word-group count per image derived from the expected
  data (40% of the recorded count; a newer Tesseract detected
  about 54% on the densest image).
- Session-scoped OCR cache fixture in tests/conftest.py: each
  image is processed once per test run and the result is
  shared by the metrics tests. The full suite runs more checks
  in less time (about 17 s for 61 tests on the reference
  machine).
- Tests for the review workflow without needing OCR:
  uploader accessible name and image filter, editing a
  word clearing that group's Braille (and export then
  refusing), a zero-record OCR run opening an error
  dialog, empty/whitespace table settings falling back
  to the defaults, and template.env being comment-only.
- Tests for upload isolation: each upload gets a private
  temporary directory and the previous one is removed.
- Machine-independent .env tests: parsing, whitespace
  handling, blank values, and OS environment precedence are
  checked against a temporary .env instead of asserting the
  content of the developer's own file (the old test hardcoded
  a C:\Liblouis path and only ran where that file existed).
- `braille-converter convert IMAGE_OR_DIR [--out DIR] [--math]
  [--layout half|full]`: a headless command-line converter for one
  image or a whole directory. It prints the four written paths per
  image, reports every failed image on stderr, exits 1 if any image
  failed and 2 for missing inputs. Run `braille-converter --help` for
  the full list.
- `--native` command-line flag for the GUI (same as
  BRAILLE_CONVERTER_NATIVE=1).
- shared braille_converter.pipeline module (group_by_word,
  translate_records) used by both the GUI and the CLI, so the
  one-Braille-string-per-word rule exists in one place.
- tests/test_cli.py and tests/test_pipeline_rules.py covering CLI
  parsing, directory expansion, per-image failure reporting, a full
  headless conversion, and the translation rules (group order,
  math selection, single Braille string per group, loud empty
  translations).
- `[native]` optional dependency group (pywebview) and tests proving
  `--native` and BRAILLE_CONVERTER_NATIVE=1 reach NiceGUI's native
  window mode. Launching a real window is covered by the manual
  accessibility checklist, not by CI.
- docs/manual-accessibility-test.md: a keyboard-only NVDA/JAWS
  checklist for startup, the full workflow, error dialogs, focus
  return, and native window mode. Linked from README and
  CONTRIBUTING.
- Ruff linting (rules E4, E7, E9, F) in CI and as a dev dependency.
  The existing code passes; two unused imports and two intentional
  script path-bootstrapping imports were adjusted.

### Changed

- Error toasts now announce only the error title. The full
  explanation remains in the modal dialog (role=alert) and the
  aria-live status region, so a long multi-paragraph toast no longer
  duplicates or obscures the dialog text for screen-reader users.
- Uploaded images are written to a private temporary directory per
  upload instead of a shared fixed path. Same-named uploads can no
  longer overwrite each other, the image file handle is closed before
  anything else touches the file (Windows would otherwise refuse to
  delete it), and the previous upload's directory is removed after a
  new image loads successfully.
- NiceGUI is now constrained to >=4.0,<5 and the app runs on 4.0.0.
  The full test suite passes unchanged on the new major version and
  the lockfile is updated.
- gui.translate_all now calls pipeline.translate_records instead of
  duplicating the grouping and math-selection logic (behavior
  unchanged; the existing GUI workflow test still covers it).
- README documents the CLI, the native extra install command, and
  the manual accessibility checklist. The unverified PyInstaller
  section was replaced with an honest packaging note.

- .gitignore now ignores the `.idea/` JetBrains IDE directory.
- The previously tracked `.idea/` files are untracked from the index
  (local copies are kept) so the ignore rule is effective.
- translator.py now produces real Unicode Braille. The previous
  Liblouis CLI call was broken in three silent ways: it omitted the
  `--forward` flag (lou_translate echoed the input back unchanged),
  it omitted the `unicode.dis` display table (output would have been
  NAB ASCII), and it decoded stdout with the Windows locale encoding
  instead of UTF-8 (Unicode Braille would have been mangled). The CLI
  is now invoked as `lou_translate --forward unicode.dis,<table>` with
  explicit UTF-8 handling.
- The default literary table is now en-ueb-g2.ctb (contracted Unified
  English Braille), replacing en-ueb-g1.ctb. The LIBLOUIS_UEB_TABLE
  and LIBLOUIS_UEB_MATH_TABLE environment variables override it as
  before.
- main.py launches the NiceGUI app (ui.run, port 8787) instead of
  creating a tkinter root window. run_app.py is unchanged and still
  works.
- Export now blocks (with an explanatory dialog) while approved word
  groups are untranslated, instead of asking whether to export anyway.
  This prevents silently producing outputs missing Braille. The
  message states how many approved words are untranslated.
- All controls carry multi-word aria-labels via quoted props; plain
  props('aria-label=Two words') is parsed by NiceGUI as several
  boolean props and truncates the label to its first word.

### Fixed

- Image preview crashed with TypeError on NiceGUI 4: ui.image takes the
  source positionally in that version, so passing src= raised
  "unexpected keyword argument 'src'". The preview is now built with a
  positional data URI.
- Export always refused with "Untranslated records" after a successful
  "Translate all". Braille is stored once per word group (on the group's
  first record) because exports render one Braille string per group,
  but the export validation demanded Braille on every approved record.
  Validation now checks per approved word group, so translated content
  can be exported.
- `.env` was tracked in git despite the `.gitignore` rule (it was
  added in the initial commit before the ignore rule existed). It is
  now untracked from the index only; the local file is untouched, and
  future changes to it will not be committed. It contains
  machine-specific table paths and must stay out of version control.
- The local .env file was malformed: both lines were missing the '='
  separator (for example LIBLOUIS_UEB_TABLE_C:\... instead of
  LIBLOUIS_UEB_TABLE=C:\...), so a dotenv parser would never have set
  either variable. Both lines are now valid KEY=VALUE pairs pointing
  at existing UEB tables.
- CI was red on every run: tests/test_pipeline.py::
  test_every_detected_word_translates declared only the Liblouis
  requirement while it also runs OCR. The CI runner installs Liblouis
  but not Tesseract, so the test failed instead of skipping. Tool
  requirements are now declared with @pytest.mark.tesseract and
  @pytest.mark.liblouis, the availability checks live once in
  tests/conftest.py (replacing three duplicated copies), and a
  collection hook turns a missing tool into a skip with a clear reason.
  A test that needs both tools declares both markers, so this class of
  bug cannot recur silently.
- Editing a record left stale Braille in place: apply_edit changed the
  text or kind but kept the old translation, so export could write
  Braille for text that no longer existed. Editing any record now
  clears that word group's Braille, says so in the status region, and
  export refuses until the word is translated again. A different word
  group keeps its translation.
- apply_edit also reported "Updated record N" when N was not in the
  current results. It now opens a "Record not found" dialog and changes
  nothing.
- An empty or whitespace-only LIBLOUIS_UEB_TABLE or
  LIBLOUIS_UEB_MATH_TABLE value produced an empty table name instead of
  falling back to the default table. get_table now treats a blank value
  as "use the default" (en-ueb-g2.ctb or en-ueb-math.ctb).
- template.env contained three blank assignments, so copying it to .env
  silently disabled both table defaults. It now contains commented-out
  examples only and documents LOU_TRANSLATE_CMD and TESSERACT_CMD.
- The image uploader had no visible label and relied on an aria-label
  that landed on its wrapper rather than its file selection control. It
  now carries label="Choose image file" plus the aria-label, and
  accept="image/*" so only images can be selected.
- OCR that detected zero characters reported success ("OCR found 0
  records") and left the user with an empty table. It now opens an
  error dialog explaining likely causes (blur, orientation, missing
  English language data) and the status region keeps the failure text.
