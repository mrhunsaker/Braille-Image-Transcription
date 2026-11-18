
"""Tests for the command-line converter."""

from pathlib import Path
import tomllib

import pytest

from braille_converter.diagnostics import (
    CheckResult,
    check_liblouis,
    check_tesseract,
    format_report,
    run_checks
)

from braille_converter.main import (
    build_parser,
    collect_images,
    main
)

TEST_DIR = Path(__file__).parent / "test_files"

SMALL_IMAGE = (
    TEST_DIR
    / "6d6670b8e65d3ff8126e5ab9aeaffbd8_img.jpg"
)


def test_translate_script_starts_the_gui_entry_point():
    """``uv run translate`` must map to the GUI entry point."""

    project = tomllib.loads(
        (
            Path(__file__).parents[1] / "pyproject.toml"
        ).read_text(encoding="utf-8")
    )

    scripts = project["project"]["scripts"]

    assert scripts["translate"] == (
        "braille_converter.main:main"
    )


def test_help_lists_convert(capsys):

    with pytest.raises(SystemExit) as exc:

        main(["--help"])

    assert exc.value.code == 0

    output = capsys.readouterr().out

    assert "convert" in output

    assert "doctor" in output


def test_doctor_help_describes_the_check(capsys):

    with pytest.raises(SystemExit) as exc:

        main(["doctor", "--help"])

    assert exc.value.code == 0

    output = capsys.readouterr().out

    assert "Tesseract" in output

    assert "Liblouis" in output


def test_doctor_reports_success(
    monkeypatch,
    capsys
):
    """A healthy environment exits 0 and names both tools."""

    good = [
        CheckResult("Tesseract OCR", True, "5.5.0"),
        CheckResult(
            "Liblouis UEB", True, "table=en-ueb-g2.ctb"
        )
    ]

    monkeypatch.setattr(
        "braille_converter.diagnostics.run_checks",
        lambda: good
    )

    assert main(["doctor"]) == 0

    output = capsys.readouterr().out

    assert "[OK] Tesseract OCR: 5.5.0" in output

    assert "All checks passed." in output


def test_doctor_reports_failure_without_gui(
    monkeypatch,
    capsys
):
    """A broken tool exits 1 and tells the user how to fix it."""

    bad = [
        CheckResult(
            "Tesseract OCR",
            False,
            "set TESSERACT_CMD to its full path"
        ),
        CheckResult("Liblouis UEB", True, "ready")
    ]

    monkeypatch.setattr(
        "braille_converter.diagnostics.run_checks",
        lambda: bad
    )

    assert main(["doctor"]) == 1

    captured = capsys.readouterr()

    assert "[PROBLEM] Tesseract OCR" in captured.out

    assert "1 check(s) failed" in captured.err

    assert "TESSERACT_CMD" in captured.out


def test_checks_are_actionable_on_missing_tools(
    monkeypatch
):
    """Failures carry guidance, never a bare False."""

    def fail(*args, **kwargs):
        raise RuntimeError("not installed")

    monkeypatch.setattr(
        "braille_converter.diagnostics.configure_tesseract",
        fail
    )

    result = check_tesseract()

    assert result.ok is False

    assert "TESSERACT_CMD" in result.detail

    monkeypatch.setattr(
        "braille_converter.diagnostics.translate_ueb",
        fail
    )

    liblouis = check_liblouis()

    assert liblouis.ok is False

    assert liblouis.detail


def test_format_report_marks_every_check():
    """No check may be omitted or silently marked OK."""

    report = format_report([
        CheckResult("One", True, "yes"),
        CheckResult("Two", False, "no")
    ])

    assert "[OK] One: yes" in report

    assert "[PROBLEM] Two: no" in report

    assert len(run_checks()) == 2


def test_convert_requires_an_input():
    """argparse must reject a bare 'convert' command."""

    with pytest.raises(SystemExit) as exc:

        build_parser().parse_args(["convert"])

    assert exc.value.code == 2


def test_missing_path_reports_error(
    tmp_path,
    capsys
):

    code = main(
        [
            "convert",
            str(tmp_path / "no_such_image.png")
        ]
    )

    assert code == 2

    error = capsys.readouterr().err

    assert "Input path not found" in error


def test_directory_is_expanded_to_images(tmp_path):

    (tmp_path / "a.jpg").write_bytes(b"x")

    (tmp_path / "b.png").write_bytes(b"x")

    (tmp_path / "notes.txt").write_text(
        "not an image",
        encoding="utf-8"
    )

    images = collect_images([str(tmp_path)])

    assert [path.name for path in images] == [
        "a.jpg",
        "b.png"
    ]


def test_empty_directory_reports_error(
    tmp_path,
    capsys
):

    code = main(
        ["convert", str(tmp_path)]
    )

    assert code == 2

    assert "No image files found" in (
        capsys.readouterr().err
    )


def test_failed_image_is_reported(
    monkeypatch,
    tmp_path,
    capsys
):

    def fail(path):

        raise RuntimeError("OCR exploded")

    monkeypatch.setattr(
        "braille_converter.ocr_engine.recognize_characters",
        fail
    )

    code = main(
        [
            "convert",
            str(SMALL_IMAGE),
            "--out",
            str(tmp_path)
        ]
    )

    error = capsys.readouterr().err

    assert code == 1

    assert "FAIL" in error

    assert "OCR exploded" in error


@pytest.mark.tesseract
@pytest.mark.liblouis
def test_convert_writes_all_outputs(
    tmp_path,
    capsys
):

    out_dir = tmp_path / "out"

    code = main(
        [
            "convert",
            str(SMALL_IMAGE),
            "--out",
            str(out_dir)
        ]
    )

    captured = capsys.readouterr()

    assert code == 0, captured.err

    written = sorted(
        path.name for path in out_dir.iterdir()
    )

    assert any(
        name.endswith("_braille.png")
        for name in written
    )

    assert any(
        name.endswith("_braille.pdf")
        for name in written
    )

    assert any(
        name.endswith("_ocr.json")
        for name in written
    )

    assert any(
        name.endswith("_tactile.svg")
        for name in written
    )

    assert len(written) == 4


def test_launch_gui_passes_native_flag(monkeypatch):

    import nicegui

    from braille_converter.main import launch_gui

    seen = {}

    monkeypatch.setattr(
        nicegui.ui,
        "run",
        lambda **kwargs: seen.update(kwargs)
    )

    assert launch_gui(native=True) == 0

    assert seen["native"] is True

    assert seen["show"] is False


def test_native_environment_variable(monkeypatch):

    import nicegui

    from braille_converter.main import launch_gui

    seen = {}

    monkeypatch.setattr(
        nicegui.ui,
        "run",
        lambda **kwargs: seen.update(kwargs)
    )

    monkeypatch.setenv(
        "BRAILLE_CONVERTER_NATIVE",
        "1"
    )

    assert launch_gui() == 0

    assert seen["native"] is True


def test_native_extra_is_declared():

    import tomllib

    config = tomllib.loads(
        (
            Path(__file__).parents[1]
            / "pyproject.toml"
        ).read_text(encoding="utf-8")
    )

    extras = config["project"][
        "optional-dependencies"
    ]

    assert "native" in extras

    assert any(
        requirement.startswith("pywebview")
        for requirement in extras["native"]
    )


def test_dependabot_watches_python_and_actions():

    config = (
        Path(__file__).parents[1]
        / ".github"
        / "dependabot.yml"
    ).read_text(encoding="utf-8")

    assert 'package-ecosystem: "uv"' in config

    assert (
        'package-ecosystem: "github-actions"'
        in config
    )

    assert 'interval: "weekly"' in config


def test_dev_extra_includes_coverage_tooling():

    import tomllib

    config = tomllib.loads(
        (
            Path(__file__).parents[1]
            / "pyproject.toml"
        ).read_text(encoding="utf-8")
    )

    dev = config["project"][
        "optional-dependencies"
    ]["dev"]

    assert any(
        requirement.startswith("pytest-cov")
        for requirement in dev
    )
