
import os

import pytest

from braille_converter.translator import (
    get_table,
    translate_ueb,
    load_env_file,
    project_root,
    TranslationError
)


@pytest.mark.liblouis
def test_translate_hello_world_g2():

    result = translate_ueb("hello world")

    assert result == "⠓⠑⠇⠇⠕⠀⠸⠺"


def test_translate_empty_is_empty():

    assert translate_ueb("") == ""


def test_env_file_loads_values(
    tmp_path,
    monkeypatch
):
    """Parsing must not depend on the machine's real .env."""

    env_path = tmp_path / ".env"

    env_path.write_text(
        "# comment line\n"
        "\n"
        "LIBLOUIS_UEB_TABLE = /tables/custom.ctb\n"
        "LIBLOUIS_UEB_MATH_TABLE=\n",
        encoding="utf-8"
    )

    monkeypatch.delenv(
        "LIBLOUIS_UEB_TABLE",
        raising=False
    )

    monkeypatch.delenv(
        "LIBLOUIS_UEB_MATH_TABLE",
        raising=False
    )

    values = load_env_file(env_path)

    assert values == {
        "LIBLOUIS_UEB_TABLE": "/tables/custom.ctb",
        "LIBLOUIS_UEB_MATH_TABLE": ""
    }

    assert (
        os.environ["LIBLOUIS_UEB_TABLE"]
        == "/tables/custom.ctb"
    )


def test_env_file_does_not_override_environment(
    tmp_path,
    monkeypatch
):
    env_path = tmp_path / ".env"

    env_path.write_text(
        "LIBLOUIS_UEB_TABLE=/from/file.ctb\n",
        encoding="utf-8"
    )

    monkeypatch.setenv(
        "LIBLOUIS_UEB_TABLE",
        "/from/environment.ctb"
    )

    values = load_env_file(env_path)

    assert (
        values["LIBLOUIS_UEB_TABLE"]
        == "/from/file.ctb"
    )

    assert (
        os.environ["LIBLOUIS_UEB_TABLE"]
        == "/from/environment.ctb"
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


def test_empty_env_table_uses_default(monkeypatch):
    """An empty .env value must not disable the default."""

    monkeypatch.setenv("LIBLOUIS_UEB_TABLE", "")

    assert get_table() == "en-ueb-g2.ctb"


def test_whitespace_math_table_uses_default(
    monkeypatch
):

    monkeypatch.setenv(
        "LIBLOUIS_UEB_MATH_TABLE",
        "   "
    )

    assert (
        get_table(math_mode=True)
        == "en-ueb-math.ctb"
    )


def test_configured_table_overrides_default(
    monkeypatch
):

    monkeypatch.setenv(
        "LIBLOUIS_UEB_TABLE",
        "/tmp/custom.ctb"
    )

    assert get_table() == "/tmp/custom.ctb"


def test_template_env_is_comments_only():

    template = project_root() / "template.env"

    assert template.exists(), (
        "template.env is missing; it documents "
        "the supported .env settings."
    )

    text = template.read_text(
        encoding="utf-8"
    )

    # Every assignment is commented out, so copying
    # the template verbatim cannot set a blank value.
    for line in text.splitlines():

        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        raise AssertionError(
            "template.env has an active setting: "
            f"{line!r}"
        )

    assert "LIBLOUIS_UEB_TABLE" in text

    assert load_env_file(template) == {}
