# TODO

Deferred work that is intentionally not part of the current change.

## Braille output spacing

The returned Braille currently concatenates the OCR text of each word
group without preserving spaces between words or lines. Derive that
spacing from the record bounding-box geometry (horizontal gaps and
vertical line breaks) so exported Braille reflects the source layout.

Deferred at the user's request while bounding-box rejection and OCR
review were completed. See the comment in
`src/braille_converter/pipeline.py::translate_records`.

The visual/tactile overlap fix is separate and complete: rendered
words are spaced, wrapped and line-shifted by
`braille_render.layout_braille_groups()` for all export formats.
That does not change the spacing inside the Braille string returned
by the translator; this item remains open.
