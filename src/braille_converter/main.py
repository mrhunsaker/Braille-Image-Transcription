
"""Command-line entry point.

Running without a subcommand starts the NiceGUI review
app. ``braille-converter convert`` runs the same OCR and
translation pipeline headlessly for one image or a
directory of images. ``braille-converter doctor`` reports
whether Tesseract and Liblouis are correctly installed.
"""

import argparse
import os
import sys
from pathlib import Path


IMAGE_SUFFIXES = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp"
}


def collect_images(inputs):
    """Expand files and directories into image paths."""

    images = []

    for item in inputs:

        path = Path(item)

        if path.is_dir():

            images.extend(
                sorted(
                    child
                    for child in path.iterdir()
                    if child.is_file()
                    and child.suffix.lower()
                    in IMAGE_SUFFIXES
                )
            )

        elif path.is_file():

            images.append(path)

        else:

            raise FileNotFoundError(
                f"Input path not found: {path}"
            )

    if not images:

        raise FileNotFoundError(
            "No image files found in: "
            + ", ".join(
                str(Path(item))
                for item in inputs
            )
        )

    return images


def convert_images(
    inputs,
    out_dir,
    math_mode=False,
    layout_name="half"
):
    """Convert images headlessly and report every failure."""

    from .braille_render import BrailleProfile

    from .image_pipeline import export_outputs

    from .layout import LAYOUTS

    from .ocr_engine import recognize_characters

    from .pipeline import translate_records

    layout = next(
        candidate
        for candidate in LAYOUTS.values()
        if candidate.name == layout_name
    )

    out_path = Path(out_dir)

    failures = 0

    for image in collect_images(inputs):

        try:

            records = recognize_characters(
                image
            )

            if not records:

                raise RuntimeError(
                    "OCR found no characters; "
                    "check image quality and "
                    "that English Tesseract "
                    "language data is installed"
                )

            translate_records(
                records,
                force_math=math_mode
            )

            paths = export_outputs(
                image,
                records,
                out_path,
                layout,
                BrailleProfile()
            )

        except Exception as exc:

            failures += 1

            print(
                f"FAIL {image.name}: {exc}",
                file=sys.stderr
            )

            continue

        print(
            f"{image.name}: "
            f"{len(records)} records, "
            f"{len(paths)} files"
        )

        for path in paths:

            print(f"  {path}")

    if failures:

        print(
            f"{failures} image(s) failed.",
            file=sys.stderr
        )

    return 1 if failures else 0


def run_doctor():
    """Print environment diagnostics and return an exit code."""

    from .diagnostics import format_report, run_checks

    results = run_checks()

    print(format_report(results))

    failed = sum(
        1 for result in results if not result.ok
    )

    if failed:
        print(
            f"{failed} check(s) failed. Fix the problems "
            "above and run 'braille-converter doctor' "
            "again.",
            file=sys.stderr
        )

        return 1

    print("All checks passed.")

    return 0


def build_parser():

    parser = argparse.ArgumentParser(
        prog="braille-converter",
        description=(
            "OCR worksheets into Unified English "
            "Braille. Without a subcommand the "
            "NiceGUI review app starts."
        )
    )

    parser.add_argument(
        "--native",
        action="store_true",
        help=(
            "start the GUI in a native window "
            "(requires the 'native' extra)"
        )
    )

    commands = parser.add_subparsers(
        dest="command"
    )

    convert = commands.add_parser(
        "convert",
        help=(
            "convert images without opening "
            "the GUI"
        )
    )

    convert.add_argument(
        "inputs",
        nargs="+",
        metavar="IMAGE_OR_DIR",
        help="an image file or a directory of images"
    )

    convert.add_argument(
        "--out",
        default="braille_output",
        metavar="DIR",
        help=(
            "output directory "
            "(default: braille_output)"
        )
    )

    convert.add_argument(
        "--math",
        action="store_true",
        help=(
            "use the math Braille table for "
            "every word"
        )
    )

    convert.add_argument(
        "--layout",
        choices=["half", "full"],
        default="half",
        help=(
            "page layout: half (8 x 5 in) or "
            "full (8 x 10.5 in)"
        )
    )

    commands.add_parser(
        "doctor",
        help=(
            "check Tesseract OCR, Liblouis and "
            "the configured Braille tables"
        ),
        description=(
            "Check Tesseract OCR, Liblouis and the "
            "configured Braille tables. Reports an "
            "actionable message for every problem and "
            "exits 1 if any check fails."
        )
    )

    return parser


def launch_gui(native=False):

    from nicegui import ui

    from . import gui  # noqa: F401 (registers the page)

    native = native or (
        os.environ.get(
            "BRAILLE_CONVERTER_NATIVE"
        )
        == "1"
    )

    try:

        ui.run(
            title=(
                "Braille Converter - "
                "OCR Review"
            ),
            port=8787,
            reload=False,
            show=not native,
            native=native
        )

    except Exception as exc:

        print(
            f"ERROR: could not start the "
            f"GUI: {exc}",
            file=sys.stderr
        )

        print(
            "For a native window install the "
            "optional dependency:",
            file=sys.stderr
        )

        print(
            "    uv sync --extra native",
            file=sys.stderr
        )

        return 1

    return 0


def main(argv=None):

    args = build_parser().parse_args(argv)

    if args.command == "convert":

        try:

            return convert_images(
                args.inputs,
                args.out,
                math_mode=args.math,
                layout_name=args.layout
            )

        except FileNotFoundError as exc:

            print(
                f"ERROR: {exc}",
                file=sys.stderr
            )

            return 2

    if args.command == "doctor":

        return run_doctor()

    return launch_gui(native=args.native)


if __name__ == "__main__":

    sys.exit(main())
