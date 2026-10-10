# Handwriting Dataset Protocol

## Purpose

The dataset trains and evaluates three bounded recognition tasks from the exam
form: student name, student number and numeric question score. Full answer text
and semantic grading are outside scope.

## Manifest

Each approved crop is represented by one JSON Lines record:

```json
{"image_path":"scores/anon-001-q1.png","label":"17.5","field_type":"score","writer_id":"writer-001","split":"train","device_class":"iphone","capture_condition":"shadow"}
```

Allowed `field_type` values are `name`, `student_number` and `score`. Allowed
splits are `train`, `validation` and `test`.

`device_class` is optional and limited to `iphone`, `android`, `scanner` or
`unknown`. `capture_condition` is optional and limited to `controlled`, `shadow`,
`glare`, `skew`, `blur`, `low_light` or `unknown`. These fixed categories enable
aggregate robustness slices without putting device identifiers or free-text notes
into the evaluation report.

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

## Split and evaluation procedure

1. Assign an anonymous writer to exactly one split before model tuning. Keep the
   test labels sealed from training and threshold selection.
2. Train only on `train`. Use `validation` for model selection and the low-confidence
   review threshold. Run the final `test` evaluation after both are frozen.
3. Include controlled captures plus approved blur, shadow, glare, skew and low-light
   cases. Record only the fixed categories above; never store phone serial numbers,
   account names or location metadata.
4. Report sample counts, inference failures, exact match, character error rate,
   numeric mean absolute error for scores, confidence calibration, low-confidence
   review rate and unflagged errors. Report device/condition slices only when each
   slice meets the minimum disclosure count.
5. An above-threshold field is merely not highlighted as low confidence. Every paper
   still requires instructor review and explicit confirmation; the threshold never
   authorizes automatic grade submission.

No model bundle may be marked production-ready until held-out writers meet the
approved thresholds and confidence calibration has been evaluated.
