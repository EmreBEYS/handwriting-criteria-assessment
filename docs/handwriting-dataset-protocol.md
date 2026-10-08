# Handwriting Dataset Protocol

## Purpose

The dataset trains and evaluates three bounded recognition tasks from the exam
form: student name, student number and numeric question score. Full answer text
and semantic grading are outside scope.

## Manifest

Each approved crop is represented by one JSON Lines record:

```json
{"image_path":"scores/anon-001-q1.png","label":"17.5","field_type":"score","writer_id":"writer-001","split":"train"}
```

Allowed `field_type` values are `name`, `student_number` and `score`. Allowed
splits are `train`, `validation` and `test`.

`writer_id` must be an anonymous, stable identifier. One writer must occur in
exactly one split. The manifest loader rejects writer leakage, duplicate image
paths, missing labels and unsupported field types before training begins.

## Privacy and quality

- Collect only with institutional approval and an explicit lawful basis.
- Keep the mapping from anonymous writer ID to a person outside the ML dataset.
- Do not commit real exam images, names or student numbers to Git.
- Include different pens, lighting, camera angles and valid decimal score styles.
- Preserve difficult but readable samples; mark unreadable samples separately
  rather than inventing a label.
- Report character error rate for names/numbers, exact-match rate for student
  numbers and numeric exact-match/error rate for scores.

No model bundle may be marked production-ready until held-out writers meet the
approved thresholds and confidence calibration has been evaluated.
