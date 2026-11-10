# Code style

This document records the style actually used in this
repository. Please follow it for new code so the project
stays consistent.

## Formatting

- One statement per line.
- A blank line between statements. This is unusual, but it
  is the established style of this codebase and it is what
  the existing code does.
- Keep lines to roughly 72-79 columns.
- Break long expressions onto continuation lines, aligned
  inside parentheses.
- Four-space indentation, no tabs.

Example:

```python
def detect_words(image):

    words = []

    for i, text in enumerate(word_data["text"]):

        text = (text or "").strip()

        if not text:
            continue
```

## Naming

- Modules, functions, variables, and parameters: lowercase
  with underscores (`recognize_characters`,
  `UNICODE_DISPLAY_TABLE` for constants).
- Classes: PascalCase (`OCRRecord`, `ConverterApp`).
- Constants: UPPER_CASE with underscores.
- Descriptive names over abbreviations.

## Imports

- Standard library first, then third-party, then local.
- Local imports use the relative package form
  (`from .models import OCRRecord`).

## Structure

- Data models are dataclasses (`models.py`).
- Type hints on public functions.
- Docstrings for public modules, classes, and functions.
- Comments explain why, not what.

## Errors

- Never fail silently. No bare `except: pass`, no
  catch-and-continue, no empty-string returns on error.
- Raise typed exceptions carrying actionable messages:
  what failed, where the code looked, and how to fix it.
- The GUI must surface every failure in an accessible
  modal dialog.

## Tests

- Plain pytest functions, no classes.
- Descriptive test names stating the behavior.
- Skip with a clear reason when an external tool
  (Tesseract, Liblouis) is unavailable.
- Every change to pipeline behavior updates
  tests/test_files/expected/ via
  `uv run python scripts/generate_expected.py` when OCR
  behavior intentionally changes.

## Changelog

- Every user-visible change adds an entry to CHANGES.md in
  the same commit as the change.
