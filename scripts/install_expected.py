
"""Install generated OCR fixtures from a CI artifact.

Example:

    uv run python scripts/install_expected.py `
        C:/Downloads/ocr-expected-ubuntu

The source may be a version directory or a root containing
several version directories. Each JSON file is validated
before anything is copied into the repository.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[1]

TARGET = (
    ROOT / "tests" / "test_files" / "expected"
)

REQUIRED_KEYS = {
    "image",
    "tesseract_version",
    "word_count",
    "min_word_count",
    "record_count",
    "words"
}


def version_dirs(source):
    """Return (version name, directory) pairs."""

    direct = sorted(
        source.glob("*_img.json")
    )

    if direct:
        return [(source.name, source)]

    pairs = []

    for path in sorted(source.iterdir()):

        if path.is_dir() and list(
            path.glob("*_img.json")
        ):
            pairs.append((path.name, path))

    return pairs


def validate(version, directory):
    """Return the fixture paths, or raise ValueError."""

    fixtures = sorted(
        directory.glob("*_img.json")
    )

    if not fixtures:
        raise ValueError(
            f"No fixtures in {directory}"
        )

    for fixture in fixtures:

        payload = json.loads(
            fixture.read_text(encoding="utf-8")
        )

        missing = REQUIRED_KEYS - payload.keys()

        if missing:
            raise ValueError(
                f"{fixture.name} is missing "
                f"keys: {sorted(missing)}"
            )

        if payload["tesseract_version"] != version:
            raise ValueError(
                f"{fixture.name} says Tesseract "
                f"{payload['tesseract_version']} "
                f"but lives in {version}/"
            )

    return fixtures


def main(argv=None):

    parser = argparse.ArgumentParser(
        description=(
            "Copy validated per-version OCR "
            "fixtures into the repository."
        )
    )

    parser.add_argument(
        "source",
        type=Path,
        help=(
            "Downloaded artifact directory, or "
            "a single version directory."
        )
    )

    parser.add_argument(
        "--version",
        help="Install only this version."
    )

    args = parser.parse_args(argv)

    source = args.source.resolve()

    if not source.is_dir():
        print(f"FAIL: not a directory: {source}")

        return 1

    pairs = version_dirs(source)

    if args.version:
        pairs = [
            pair for pair in pairs
            if pair[0] == args.version
        ]

    if not pairs:
        print(
            "FAIL: no versioned fixtures found "
            f"in {source}"
        )

        return 1

    installed = 0

    for version, directory in pairs:

        fixtures = validate(
            version,
            directory
        )

        target_dir = TARGET / version

        target_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        for fixture in fixtures:

            shutil.copy2(
                fixture,
                target_dir / fixture.name
            )

            installed += 1

        print(
            f"Installed {len(fixtures)} "
            f"fixtures for Tesseract {version}"
        )

    print(f"{installed} file(s) copied into {TARGET}")

    return 0


if __name__ == "__main__":

    sys.exit(main())
