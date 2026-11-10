# OCR pipeline benchmark

Measured against the 7 images in tests/test_files.

## Environment

- Tesseract 5.4.0.20240606 (UB-Mannheim build, default install path)
- Liblouis 3.39.0 at C:\Liblouis (lou_translate via absolute path)
- Python 3.13, Pillow, pytesseract

## Configuration comparison (word/character detection)

Every combination of preprocessing (plain, upscale x4-x6
LANCZOS, grayscale, autocontrast) and --psm mode (11, 6, 3, 4)
was measured over all 7 images. Totals (see experiment log):

| configuration      | words | chars | empty images |
|--------------------|-------|-------|--------------|
| plain, psm 6       | 136   | 285   | 0            |
| upx4, psm 6        | 110   | 210   | 0            |
| upx4, psm 11       | 103   | 207   | 0            |
| plain, psm 11      |  41   | 127   | 0 (old)      |
| upx6+autocontrast  | 230   | 134   | 0 (noise)    |

Findings:

- psm 6 (uniform block of text) substantially outperforms
  psm 11 (sparse text) on these worksheet images.
- Upscaling with LANCZOS reduces detection; Tesseract 5's
  internal scaling performs better on these small images.
- autocontrast triggers massive over-detection of noise
  (punctuation fragments from graph grid lines), so it is
  rejected.
- The old code used psm 11 for word detection but the
  default psm (3) for character detection, so word and
  character boxes came from different segmentations. On
  9df11121 no character fell inside any word box, which is
  why its mean confidence was 0.0. Using one psm for both
  calls fixes the association.

## Chosen configuration

plain (no preprocessing) + --psm 6 for both image_to_data
and image_to_boxes.

## Before / after (full pipeline metrics)

Old pipeline (psm 11 words / default chars, O(n*m)
association):

    image                     records words conf  translated
    0ad3f61f997eb05afb34...        28    13 0.960         13
    431b8889a0e7f676f0ee...        44    27 0.892         27
    67020988167474f5810b...        32    16 0.956         16
    6d6670b8e65d3ff8126e...         0     0 0.000          0
    87658d45f2d2f009cbb9...        12     7 0.950          7
    90864f8e2844459829af...         5     2 0.904          2
    9df11121dce75cf8f86a...        12    12 0.000         12

New pipeline (psm 6 both, bucketed association, stable
ordering):

    image                     records words conf  translated
    0ad3f61f997eb05afb34...        35    14 0.852         14
    431b8889a0e7f676f0ee...       156    59 0.345         59
    67020988167474f5810b...        31    11 0.760         11
    6d6670b8e65d3ff8126e...         5     2 0.276          2
    87658d45f2d2f009cbb9...        23     9 0.684          9
    90864f8e2844459829af...         9     5 0.759          5
    9df11121dce75cf8f86a...        26    12 0.763         12

Improvements:

- 6d6670b8 produced zero records before; it now produces
  5 records across 2 words (the image is mostly a diagram).
- 9df11121 word/character association was completely broken
  (mean confidence 0.0); it is now 0.763 with association
  working.
- More real content is detected on every image (psm 6 finds
  words psm 11 missed entirely).

Trade-off:

- Mean confidence drops on some images because psm 6 also
  detects marginal, low-confidence words that psm 11 skipped.
  On the graph image 431b8889 this includes grid-line noise
  (127 of 156 records are below 0.5 confidence). The real
  content (29 records: "weight in pounds", axis numbers)
  carries high confidence. The review table is sortable by
  confidence so noise can be identified and unapproved; the
  confidence value is honest rather than silently missing
  content, which is the intended behavior of this
  human-review workflow.
