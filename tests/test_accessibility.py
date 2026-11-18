
"""Automated guards for the screen-reader-facing UI.

Manual NVDA/JAWS testing is still required, but these
assertions catch regressions that can be checked in code:
missing accessible names, lost live regions and unlabelled
dialogs.
"""

from pathlib import Path

from nicegui import ui

from nicegui.testing import user_simulation

from braille_converter.gui import ConverterApp

from braille_converter.models import OCRRecord

SAMPLE_IMAGE = (
    Path(__file__).parent
    / "test_files"
    / "67020988167474f5810b295ba0fdc993_img.jpg"
)


INTERACTIVE = (
    ui.button,
    ui.input,
    ui.number,
    ui.select,
    ui.checkbox,
    ui.upload
)


def make_root(holder):

    def root():

        holder["app"] = ConverterApp()

    return root


def accessible_name(element):

    props = element.props or {}

    return (
        props.get("aria-label")
        or getattr(element, "label", None)
        or getattr(element, "text", None)
    )


async def test_every_interactive_control_has_a_name():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        elements = holder[
            "app"
        ].status_label.client.elements.values()

        controls = [
            element
            for element in elements
            if isinstance(element, INTERACTIVE)
        ]

        assert len(controls) >= 8, (
            "Expected the full workflow to be present."
        )

        unnamed = [
            type(element).__name__
            for element in controls
            if not accessible_name(element)
        ]

        assert not unnamed, (
            "Controls without accessible names: "
            + ", ".join(unnamed)
        )


async def test_live_regions_and_dialog_role():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        assert app.status_label.props.get(
            "aria-live"
        ) == "polite"

        roles = [
            element.props.get("role")
            for element in app.status_label.client
            .elements.values()
        ]

        assert "alert" in roles, (
            "The error dialog must expose role=alert."
        )

        with app.status_label:

            app.show_error(
                "Accessibility check",
                "This message must be announced."
            )

        assert app.error_message.props.get(
            "aria-live"
        ) == "assertive"

        assert app.error_message.text == (
            "This message must be announced."
        )


async def test_table_and_landmarks_are_named():

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        assert app.table.props.get(
            "aria-label"
        ) == "OCR character review results"

        groups = [
            element
            for element in app.status_label.client
            .elements.values()
            if element.props.get("role") == "group"
        ]

        names = {
            element.props.get("aria-label")
            for element in groups
        }

        assert "Selected character editor" in names

        assert "Bounding box visualization" in names

        assert "Manual bounding box creator" in names

        assert "Original image preview" in names

        assert "Altered image preview" in names

        assert "Output settings" in names

        assert app.box_summary.props.get(
            "aria-live"
        ) == "polite"

        assert app.altered_label.props.get(
            "aria-live"
        ) == "polite"

        # A generic Quasar file input is not enough: the
        # uploader itself must accept images and be named.
        assert app.upload.label == "Choose image file"

        assert app.upload.props.get(
            "accept"
        ) == "image/*"


async def test_visualization_images_have_alt_text():

    """The new visuals must not be bare, silent images."""

    holder = {}

    async with user_simulation(
        root=make_root(holder)
    ) as user:

        await user.open("/")

        app = holder["app"]

        app.image_path = SAMPLE_IMAGE

        app.records = [
            OCRRecord(
                id=7,
                text="x",
                x1=5,
                y1=5,
                x2=20,
                y2=20,
                group_id="g1",
                braille="⠭"
            )
        ]

        with app.status_label:

            await app._refresh_visualizations(
                "updated"
            )

        for image in (
            app.original_preview_image,
            app.box_image,
            app.altered_preview_image
        ):

            alt = image.props.get("alt")

            assert alt, (
                "A visualization image has no alt text."
            )

            assert '"' not in alt, (
                "Alt text must not break the HTML attribute."
            )

        assert "ID 7" in app.box_image.props["alt"]

