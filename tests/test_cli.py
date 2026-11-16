
"""Tests for the command-line converter."""

from pathlib import Path

import pytest

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


def test_help_lists_convert(capsys):

    with pytest.raises(SystemExit) as exc:

        main(["--help"])

    assert exc.value.code == 0

    output = capsys.readouterr().out

    assert "convert" in output


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
