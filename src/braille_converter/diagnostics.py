
"""Environment checks shared by the GUI and ``doctor``.

Everything is reported through CheckResult: a failed check
always carries an actionable message, never a bare boolean.
The GUI shows the same details the CLI prints.
"""

from dataclasses import dataclass

from .ocr_engine import configure_tesseract
from .translator import (
    TranslationError,
    find_lou_translate,
    get_table,
    load_env_file,
    translate_ueb,
    translation_timeout
)


@dataclass
class CheckResult:
    """The outcome of one environment check."""

    name: str
    ok: bool
    detail: str


def check_tesseract():
    """Verify Tesseract is installed and report its version."""

    try:
        import pytesseract

        configure_tesseract()

        version = str(
            pytesseract.get_tesseract_version()
        ).strip()

        executable = (
            pytesseract.pytesseract.tesseract_cmd
        )

        return CheckResult(
            "Tesseract OCR",
            True,
            f"{version} at {executable}"
        )

    except Exception as exc:
        return CheckResult(
            "Tesseract OCR",
            False,
            "Tesseract OCR is not available: "
            f"{exc}. Install Tesseract (for example "
            "with 'winget install -e --id "
            "UB-Mannheim.TesseractOCR'), make sure "
            "tesseract is on PATH, or set "
            "TESSERACT_CMD to its full path."
        )


def check_liblouis():
    """Verify Liblouis and the UEB tables are usable."""

    try:
        load_env_file()

        table = get_table()
        math_table = get_table(math_mode=True)
        timeout = translation_timeout()

        translated = translate_ueb("a")

        if not translated:
            raise TranslationError(
                "Liblouis returned an empty "
                "translation for a test word."
            )

        try:
            import louis  # noqa: F401

            backend = "Python binding"

        except ImportError:
            backend = find_lou_translate() or (
                "unknown executable"
            )

        return CheckResult(
            "Liblouis UEB",
            True,
            f"table={table}, math_table={math_table}, "
            f"timeout={timeout:g}s, backend={backend}, "
            f"sample='{translated}'"
        )

    except TranslationError as exc:
        return CheckResult(
            "Liblouis UEB",
            False,
            str(exc)
        )

    except Exception as exc:
        return CheckResult(
            "Liblouis UEB",
            False,
            f"Unexpected Liblouis check failure: {exc}"
        )


def run_checks():
    """Return every environment check in report order."""

    return [
        check_tesseract(),
        check_liblouis()
    ]


def format_report(results):
    """Render check results as plain, readable text."""

    lines = []

    for result in results:

        status = "OK" if result.ok else "PROBLEM"

        lines.append(
            f"[{status}] {result.name}: {result.detail}"
        )

    return "\n".join(lines)
