
import os
import shutil
import subprocess
from pathlib import Path


class TranslationError(RuntimeError):
    pass


def get_table(math_mode=False):

    # Both tables are supplied by Liblouis.
    # The literary UEB table also includes UEB math definitions.
    if math_mode:
        return os.environ.get(
            "LIBLOUIS_UEB_MATH_TABLE",
            "en-ueb-math.ctb"
        )

    return os.environ.get(
        "LIBLOUIS_UEB_TABLE",
        "en-ueb-g1.ctb"
    )


def translate_ueb(text, math_mode=False):

    if not text:
        return ""

    table = get_table(math_mode)

    # Try the Python Liblouis binding first.
    try:

        import louis

        result = louis.translateString(
            [table],
            text
        )

        return str(result)

    except ImportError:
        pass

    except Exception as exc:

        raise TranslationError(
            f"Liblouis Python translation failed: {exc}"
        ) from exc

    # Otherwise try the Liblouis command-line executable.
    executable = shutil.which("lou_translate")

    if not executable:

        raise TranslationError(
            "Liblouis was not found. Install Liblouis "
            "and its UEB tables."
        )

    try:

        result = subprocess.run(
            [executable, table],
            input=text,
            text=True,
            capture_output=True,
            check=True
        )

        return result.stdout.rstrip("\n")

    except subprocess.CalledProcessError as exc:

        raise TranslationError(
            f"Liblouis translation failed: "
            f"{exc.stderr.strip()}"
        ) from exc
