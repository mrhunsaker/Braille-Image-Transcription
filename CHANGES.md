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

### Changed

- .gitignore now ignores the `.idea/` JetBrains IDE directory.
- translator.py now produces real Unicode Braille. The previous
  Liblouis CLI call was broken in three silent ways: it omitted the
  `--forward` flag (lou_translate echoed the input back unchanged),
  it omitted the `unicode.dis` display table (output would have been
  NAB ASCII), and it decoded stdout with the Windows locale encoding
  instead of UTF-8 (Unicode Braille would have been mangled). The
  CLI is now invoked as `lou_translate --forward unicode.dis,<table>`
  with explicit UTF-8 handling.
- The default literary table is now en-ueb-g2.ctb (contracted
  Unified English Braille), replacing en-ueb-g1.ctb. The
  LIBLOUIS_UEB_TABLE and LIBLOUIS_UEB_MATH_TABLE environment
  variables override it as before.

### Added

- .env loading (dependency-free). Values are applied at startup;
  existing OS environment variables take precedence. Malformed lines
  (missing '=' or empty key) raise TranslationError with the line
  number and file path instead of being skipped silently.
- lou_translate discovery now checks, in order: the
  LOU_TRANSLATE_CMD environment variable, the system PATH, and
  common install locations (including C:\Liblouis\bin on Windows).
  When nothing is found, TranslationError lists every location
  checked and how to fix it.
- Table existence checking: absolute table paths that do not exist
  raise TranslationError before any subprocess runs.
- tests/test_translator.py covering g2 translation, .env loading,
  malformed .env rejection, missing-table errors, and empty input.
  Liblouis-dependent tests skip with a clear reason when Liblouis
  is unavailable.

### Fixed

- `.env` was tracked in git despite the `.gitignore` rule (it was added in
  the initial commit before the ignore rule existed). It is now untracked
  from the index only; the local file is untouched, and future changes to
  it will not be committed. It contains machine-specific table paths and
  must stay out of version control.
