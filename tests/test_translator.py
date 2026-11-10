
import shutil

import pytest

from braille_converter.translator import (
    translate_ueb,
    load_env_file,
    find_lou_translate,
    project_root,
    TranslationError
)


def liblouis_available():
    """True when a usable Liblouis is installed."""

    try:
        import louis

        return True

    except ImportError:
        return bool(find_lou_translate())


needs_liblouis = pytest.mark.skipif(
    not liblouis_available(),
    reason="Liblouis with UEB tables is "
    "not installed on this machine"
)


@needs_liblouis
def test_translate_hello_world_g2():

    result = translate_ueb("hello world")

    assert result == "⠓⠑⠇⠇⠕⠀⠸⠺"


def test_translate_empty_is_empty():

    assert translate_ueb("") == ""


def test_env_file_loads_and_validates():

    env_path = (
        project_root() / ".env"
    )

    if not env_path.exists():
        pytest.skip(
            "No .env file on this machine"
        )

    values = load_env_file()

    assert (
        values.get("LIBLOUIS_UEB_TABLE")
        == r"C:\Liblouis\share\liblouis"
        r"\tables\en-ueb-g2.ctb"
    )


def test_malformed_env_line_is_loud(tmp_path):

    bad = tmp_path / ".env"

    bad.write_text(
        "MISSING_SEPARATOR_VALUE\n",
        encoding="utf-8"
    )

    try:
        load_env_file(bad)

    except TranslationError as exc:
        assert "Malformed" in str(exc)

    else:
        raise AssertionError(
            "Malformed .env line was accepted "
            "silently."
        )


def test_missing_table_path_is_loud(
    tmp_path,
    monkeypatch
):

    missing = (
        tmp_path / "no_such_table.ctb"
    )

    monkeypatch.setenv(
        "LIBLOUIS_UEB_TABLE",
        str(missing)
    )

    try:
        translate_ueb("x")

    except TranslationError as exc:
        assert "not found" in str(exc)

    else:
        raise AssertionError(
            "Missing table was accepted silently."
        )
