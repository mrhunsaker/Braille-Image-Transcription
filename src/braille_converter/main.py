
import os

from nicegui import ui

from . import gui


def main():
    """Launch the NiceGUI Braille converter."""

    native = (
        os.environ.get(
            "BRAILLE_CONVERTER_NATIVE"
        )
        == "1"
    )

    ui.run(
        title="Braille Converter - OCR Review",
        port=8787,
        reload=False,
        show=not native,
        native=native
    )


if __name__ == "__main__":

    main()
