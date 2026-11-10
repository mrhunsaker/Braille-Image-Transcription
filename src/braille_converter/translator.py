
import os
import shutil
import subprocess
from pathlib import Path


class TranslationError(RuntimeError):
    pass


# Display table that renders output as Unicode braille
# patterns instead of the default NAB ASCII charset.
UNICODE_DISPLAY_TABLE = "unicode.dis"


# Common install locations for the lou_translate CLI,
# used when the executable is not on PATH.
COMMON_CLI_LOCATIONS = [
    Path(
        r"C:\Liblouis\bin\lou_translate.exe"
    ),
    Path("/usr/bin/lou_translate"),
    Path("/usr/local/bin/lou_translate"),
]


def project_root():
    """Return the repository root for .env discovery."""

    return Path(
        __file__
    ).resolve().parents[2]


def load_env_file(path=None):
    """
    Load KEY=VALUE pairs from a .env file.

    Existing OS environment variables take precedence
    over values from the file.

    Raises TranslationError for malformed lines instead
    of skipping them silently.
    """

    if path is None:
        path = project_root() / ".env"

    path = Path(path)

    if not path.exists():
        return {}

    values = {}

    for number, raw in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1
    ):

        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            raise TranslationError(
                f"Malformed line {number} in "
                f"{path}: {raw!r}. Expected "
                "'KEY=VALUE'. Fix the line or "
                "remove it."
            )

        key, value = line.split(
            "=",
            1
        )

        key = key.strip()

        if not key:
            raise TranslationError(
                f"Malformed line {number} in "
                f"{path}: {raw!r}. The key "
                "before '=' is empty."
            )

        if key not in os.environ:
            os.environ[key] = value.strip()

        values[key] = value.strip()

    return values


def get_table(math_mode=False):
    """
    Return the Liblouis table for the request.

    The literary default is contracted Unified English
    Braille (en-ueb-g2.ctb). The LIBLOUIS_UEB_TABLE and
    LIBLOUIS_UEB_MATH_TABLE environment variables, and
    matching .env entries, override the defaults.
    """

    load_env_file()

    if math_mode:
        return os.environ.get(
            "LIBLOUIS_UEB_MATH_TABLE",
            "en-ueb-math.ctb"
        )

    return os.environ.get(
        "LIBLOUIS_UEB_TABLE",
        "en-ueb-g2.ctb"
    )


def find_lou_translate():
    """
    Locate the lou_translate executable.

    Search order: the LOU_TRANSLATE_CMD environment
    variable, the system PATH, then common install
    locations.

    Returns None when nothing is found.
    """

    configured = os.environ.get(
        "LOU_TRANSLATE_CMD"
    )

    if configured:
        candidate = Path(configured)

        if candidate.exists():
            return str(candidate)

    on_path = shutil.which(
        "lou_translate"
    )

    if on_path:
        return on_path

    for candidate in COMMON_CLI_LOCATIONS:

        if candidate.exists():
            return str(candidate)

    return None


def check_table(table):
    """
    Verify that a table reference is usable.

    Absolute paths must exist. Bare table names are
    resolved by the Liblouis CLI, so only the display
    table name is checked here.
    """

    if Path(table).is_absolute():

        if not Path(table).exists():
            raise TranslationError(
                f"Braille table not found: "
                f"{table}. Set LIBLOUIS_UEB_TABLE "
                "or LIBLOUIS_UEB_MATH_TABLE to a "
                "valid table file."
            )


def translate_ueb(text, math_mode=False):
    """
    Translate text into Unicode Braille.

    Raises TranslationError with actionable detail for
    every failure. Never returns a silent empty result.
    """

    if not text:
        return ""

    table = get_table(math_mode)

    check_table(table)

    table_list = (
        f"{UNICODE_DISPLAY_TABLE},{table}"
    )

    # Try the Python Liblouis binding first.
    try:
        import louis

        result = louis.translateString(
            [
                UNICODE_DISPLAY_TABLE,
                table
            ],
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
    executable = find_lou_translate()

    if not executable:
        searched = [
            "LOU_TRANSLATE_CMD environment variable",
            "the system PATH",
            *[
                str(location)
                for location in COMMON_CLI_LOCATIONS
            ]
        ]

        raise TranslationError(
            "Liblouis was not found. Install "
            "Liblouis with its UEB tables, add its "
            "bin directory to PATH (for example "
            "C:\\Liblouis\\bin), or set "
            "LOU_TRANSLATE_CMD to the full path of "
            "lou_translate. Locations checked: "
            + "; ".join(searched)
            + "."
        )

    try:
        result = subprocess.run(
            [
                executable,
                "--forward",
                table_list
            ],
            input=text,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )

        if not result.stdout:
            raise TranslationError(
                "Liblouis produced no output for "
                f"table {table_list}."
            )

        return result.stdout.rstrip("\r\n")

    except subprocess.CalledProcessError as exc:
        stderr = (
            exc.stderr or ""
        ).strip()

        raise TranslationError(
            f"Liblouis translation failed with "
            f"table {table_list}: {stderr or exc}"
        ) from exc

    except OSError as exc:
        raise TranslationError(
            f"Could not run lou_translate at "
            f"{executable}: {exc}"
        ) from exc
