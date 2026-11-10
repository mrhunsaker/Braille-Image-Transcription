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

### Fixed

- `.env` was tracked in git despite the `.gitignore` rule (it was added in
  the initial commit before the ignore rule existed). It is now untracked
  from the index only; the local file is untouched, and future changes to
  it will not be committed. It contains machine-specific table paths and
  must stay out of version control.
