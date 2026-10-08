# 00-10 — Exam Paper Layout Extraction

## Scope

Sprint 00-10 converts a photographed first page into stable image regions for
the handwriting pipeline:

`Uploaded page → Orientation and quality checks → Template regions → Dynamic score cells`

The initial versioned template represents the İnönü University Faculty of
Engineering exam form supplied for the project. It extracts course identity,
student name, student number, the question–program-outcome header and one score
cell per configured exam question.

## Design decisions

- Field coordinates are normalized rather than tied to one image resolution.
- Landscape captures are rotated and every page is resized to a canonical A4 frame.
- The score row is divided by the exam's configured question count; four fixed
  columns are not assumed.
- Dark, overexposed and low-detail captures produce explicit warnings.
- Invalid images, low-resolution pages and impossible question counts fail
  before OCR.
- Template configuration is versioned separately from model weights.

Perspective correction and support for additional institutional forms can be
added as new layout implementations without changing the OCR or API contracts.
