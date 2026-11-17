
import os
import subprocess
import sys
import types

import pytest

from braille_converter import translator as translator_module

from braille_converter.translator import (
    get_table,
    translate_ueb,
    load_env_file,
    project_root,
    translation_timeout,
    TranslationError
)


ENV_KEYS = (
    "LIBLOUIS_UEB_TABLE",
    "LIBLOUIS_UEB_MATH_TABLE",
    "LIBLOUIS_TIMEOUT"
)


@pytest.fixture(autouse=True)
def restore_liblouis_env():
    """Undo values load_env_file writes straight to os.environ.

    Without this, one test's temporary `.env` leaks into later
    tests. On Linux the leaked absolute table path even makes
    check_table fail, so CI caught what Windows did not.
    """

    saved = {
        key: os.environ.get(key)
        for key in ENV_KEYS
    }

    yield

    for key, value in saved.items():

        if value is None:
            os.environ.pop(key, None)

        else:
            os.environ[key] = value


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


def test_binding_empty_output_is_loud(monkeypatch):
    """A non-empty input must never produce silent Braille."""

    fake = types.ModuleType("louis")

    fake.translateString = lambda tables, text: ""

    monkeypatch.setitem(sys.modules, "louis", fake)

    with pytest.raises(TranslationError, match="no output"):

        translate_ueb("hello")


def test_subprocess_timeout_is_loud(monkeypatch):
    """A hung lou_translate must report, never hang."""

    monkeypatch.setitem(sys.modules, "louis", None)

    monkeypatch.setattr(
        translator_module,
        "find_lou_translate",
        lambda: "/fake/lou_translate"
    )

    def hang(*args, **kwargs):

        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=7.5
        )

    monkeypatch.setattr(
        translator_module.subprocess,
        "run",
        hang
    )

    with pytest.raises(
        TranslationError,
        match="timed out after 7.5 seconds"
    ):

        translate_ueb("hello")


def test_subprocess_uses_strict_decode_and_timeout(
    monkeypatch
):
    """Loud decode failures and a bounded subprocess."""

    monkeypatch.setitem(sys.modules, "louis", None)

    monkeypatch.setenv("LIBLOUIS_TIMEOUT", "5")

    monkeypatch.setattr(
        translator_module,
        "find_lou_translate",
        lambda: "/fake/lou_translate"
    )

    captured = {}

    def record(*args, **kwargs):

        captured.update(kwargs)

        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="⠁\n",
            stderr=""
        )

    monkeypatch.setattr(
        translator_module.subprocess,
        "run",
        record
    )

    assert translate_ueb("a") == "⠁"

    assert captured["errors"] == "strict"

    assert captured["timeout"] == 5.0


def test_subprocess_invalid_utf8_is_loud(monkeypatch):
    """Replacement characters must never reach Braille."""

    monkeypatch.setitem(sys.modules, "louis", None)

    monkeypatch.setattr(
        translator_module,
        "find_lou_translate",
        lambda: "/fake/lou_translate"
    )

    def corrupt(*args, **kwargs):

        raise UnicodeDecodeError(
            "utf-8",
            b"\xff",
            0,
            1,
            "invalid start byte"
        )

    monkeypatch.setattr(
        translator_module.subprocess,
        "run",
        corrupt
    )

    with pytest.raises(
        TranslationError,
        match="not valid UTF-8"
    ):

        translate_ueb("hello")


@pytest.mark.parametrize("value", ["abc", "0", "-3"])
def test_invalid_timeout_is_loud(value, monkeypatch):

    monkeypatch.setenv("LIBLOUIS_TIMEOUT", value)

    with pytest.raises(
        TranslationError,
        match="positive number of seconds"
    ):

        translation_timeout()


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
