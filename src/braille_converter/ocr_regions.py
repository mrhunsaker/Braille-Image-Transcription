
"""OpenCV helpers for proposing text and fraction regions.

These detectors never recognize text themselves. They find
candidate areas that are then passed to Tesseract by the OCR
engine, so every accepted character still has a Tesseract box.
"""

import cv2
import numpy as np


THRESHOLDS = (80, 120)

MIN_COMPONENT_WIDTH = 2

MAX_COMPONENT_WIDTH = 40

MIN_COMPONENT_HEIGHT = 4

MAX_COMPONENT_HEIGHT = 40

MIN_COMPONENT_AREA = 8

MAX_COMPONENT_ASPECT = 8

LINE_OVERLAP_PAD = 12

MAX_GROUP_GAP = 30

MIN_BAR_WIDTH = 12

MAX_BAR_WIDTH = 60

MAX_BAR_HEIGHT = 4

BAR_SEARCH_DISTANCE = 30

BAR_SEARCH_PAD = 8

MIN_BAR_ASPECT = 4


def _iou(first, second):
    """Return IoU for two ``(x1, y1, x2, y2)`` boxes."""

    x1 = max(first[0], second[0])

    y1 = max(first[1], second[1])

    x2 = min(first[2], second[2])

    y2 = min(first[3], second[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    overlap = (x2 - x1) * (y2 - y1)

    first_area = (first[2] - first[0]) * (
        first[3] - first[1]
    )

    second_area = (second[2] - second[0]) * (
        second[3] - second[1]
    )

    return overlap / max(
        first_area + second_area - overlap,
        1
    )


def _deduplicate(boxes, threshold=0.6):
    """Drop boxes that largely overlap an earlier box."""

    kept = []

    for box in boxes:

        if not any(
            _iou(box, other) > threshold
            for other in kept
        ):
            kept.append(box)

    return kept


def _binary(image, threshold):
    """Return a dark-pixel binary image."""

    gray = np.array(image.convert("L"))

    return (
        gray < threshold
    ).astype(np.uint8) * 255


def _contour_boxes(binary):
    """Return all outer contour boxes in a binary image."""

    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    return [
        cv2.boundingRect(contour)
        for contour in contours
    ]


def _glyph_components(image, threshold):
    """Return glyph-sized dark components in xyxy form."""

    components = []

    for x, y, w, h in _contour_boxes(
        _binary(image, threshold)
    ):

        aspect = w / max(h, 1)

        if (
            MIN_COMPONENT_WIDTH <= w
            <= MAX_COMPONENT_WIDTH
            and MIN_COMPONENT_HEIGHT <= h
            <= MAX_COMPONENT_HEIGHT
            and w * h >= MIN_COMPONENT_AREA
            and aspect <= MAX_COMPONENT_ASPECT
        ):
            components.append(
                (x, y, x + w, y + h)
            )

    return components


def _line_clusters(components):
    """Group components whose vertical spans overlap."""

    clusters = []

    for component in sorted(
        components,
        key=lambda box: (box[1], box[0])
    ):

        for cluster in clusters:

            if (
                component[1]
                <= max(b[3] for b in cluster)
                + LINE_OVERLAP_PAD
                and component[3] + LINE_OVERLAP_PAD
                >= min(b[1] for b in cluster)
            ):
                cluster.append(component)

                break

        else:
            clusters.append([component])

    return clusters


def _horizontal_groups(cluster):
    """Split one line cluster by large horizontal gaps."""

    groups = []

    for component in sorted(
        cluster,
        key=lambda box: box[0]
    ):

        if groups:

            right = max(
                group[2] for group in groups[-1]
            )

            if component[0] - right <= MAX_GROUP_GAP:

                groups[-1].append(component)

                continue

        groups.append([component])

    return groups


def _group_box(group):
    """Return the union of a component group."""

    return (
        min(box[0] for box in group),
        min(box[1] for box in group),
        max(box[2] for box in group),
        max(box[3] for box in group)
    )


def detect_text_regions(image):
    """Return candidate text boxes in original coordinates.

    Small dark components are grouped into lines instead of
    closing the full binary image. Morphological closing on
    these mostly white worksheets merges geometry and text
    into one image-sized region.
    """

    candidates = []

    for threshold in THRESHOLDS:

        components = _glyph_components(
            image,
            threshold
        )

        for cluster in _line_clusters(components):

            for group in _horizontal_groups(cluster):

                x1, y1, x2, y2 = _group_box(
                    group
                )

                if x2 - x1 >= 8 and y2 - y1 >= 6:

                    candidates.append(
                        (x1, y1, x2, y2)
                    )

    return _deduplicate(candidates)


def _bar_candidates(binary):
    """Return short horizontal runs from a binary image."""

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (8, 1)
    )

    opened = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel
    )

    bars = []

    for x, y, w, h in _contour_boxes(opened):

        aspect = w / max(h, 1)

        if (
            MIN_BAR_WIDTH <= w <= MAX_BAR_WIDTH
            and h <= MAX_BAR_HEIGHT
            and aspect >= MIN_BAR_ASPECT
        ):
            bars.append(
                (x, y, x + w, y + h)
            )

    return bars


def _component_between(component, bar, above):
    """Return whether a component sits above or below a bar."""

    center_x = (
        component[0] + component[2]
    ) / 2

    if not (
        bar[0] - BAR_SEARCH_PAD
        <= center_x
        <= bar[2] + BAR_SEARCH_PAD
    ):
        return False

    if above:
        return (
            0
            <= bar[1] - component[3]
            <= BAR_SEARCH_DISTANCE
        )

    return (
        0
        <= component[1] - bar[3]
        <= BAR_SEARCH_DISTANCE
    )


def detect_fraction_parts(image):
    """Return bars with their glyph components.

    Each item is ``(bar, above, below)``. The component lists
    let the OCR engine render a clean numerator/denominator
    without the diagram lines that surround many fractions.
    """

    binary = _binary(image, THRESHOLDS[0])

    components = _glyph_components(
        image,
        THRESHOLDS[0]
    )

    parts = []

    for bar in _bar_candidates(binary):

        above = [
            component
            for component in components
            if _component_between(
                component,
                bar,
                True
            )
        ]

        below = [
            component
            for component in components
            if _component_between(
                component,
                bar,
                False
            )
        ]

        if above and below:
            parts.append(
                (bar, above, below)
            )

    return parts


def detect_fraction_bars(image):
    """Return bars with glyph components above and below."""

    return _deduplicate(
        [bar for bar, _, _ in detect_fraction_parts(image)],
        threshold=0.3
    )


def uncovered_candidate_regions(regions, records, overlap=0.25):
    """Return proposals that do not overlap accepted boxes."""

    boxes = [
        (
            record.x1,
            record.y1,
            record.x2,
            record.y2
        )
        for record in records
    ]

    return [
        region
        for region in regions
        if not any(
            _iou(region, box) > overlap
            for box in boxes
        )
    ]
