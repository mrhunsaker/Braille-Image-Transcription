# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
  columns for id, text, kind, confidence, approved, box, and braille.
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

### Changed

- .gitignore now ignores the `.idea/` JetBrains IDE directory.
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
- Export now blocks (with an explanatory dialog) while approved
  records are untranslated, instead of asking whether to export
  anyway. This prevents silently producing outputs missing Braille.
- All controls carry multi-word aria-labels via quoted props; plain
  props('aria-label=Two words') is parsed by NiceGUI as several
  boolean props and truncates the label to its first word.

### Fixed

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
