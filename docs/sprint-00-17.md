# 00-17 — OCR Accuracy & Model Optimization

## Scope

Sprint 00-17 makes OCR quality measurable without inventing a benchmark result:

`Approved writer-disjoint data → validation threshold → locked test metrics → human review`

## Delivered behavior

- A deterministic evaluator reads the existing JSON Lines manifest and rejects writer leakage.
- Score and student-number crops are evaluated with exact match and character error rate; score
  evaluation also reports numeric mean absolute error.
- Confidence quality is reported with ten-bin expected calibration error.
- The low-confidence flag threshold is selected only on the validation split for a requested
  unflagged-field accuracy target, then applied unchanged to the test split.
- If validation cannot satisfy the target, field passing is disabled and every field is flagged.
- Threshold selection also requires a minimum number of unflagged validation samples (30 by
  default), preventing a misleading policy based on one or two easy examples.
- Error analysis reports aggregate inference/substitution/insertion/deletion counts. It never writes
  labels, image paths, writer IDs or individual predictions to the report.
- Optional device and capture-condition metrics are emitted only for groups meeting the configured
  minimum slice size.
- Model and manifest SHA-256 values make a report traceable to exact local artifacts.

Install the ML dependencies and run:

```bash
python -m pip install -e '.[dev,ml]'
evaluate-handwriting \
  --manifest data/processed/manifest.jsonl \
  --dataset-root data/processed \
  --model models/emnist-digits-v1.pt \
  --target-unflagged-accuracy 0.98 \
  --output ml/runs/emnist-digits-v1-evaluation.json
```

The resulting threshold is a candidate for `HCA_REVIEW_CONFIDENCE_THRESHOLD` only after an
authorized reviewer approves the dataset, report and operational trade-off. A field above the
threshold is not an automatically accepted grade: Sprint 00-12 instructor confirmation remains
mandatory for every paper.

## Verification status and limitations

Unit tests cover normalization, exact match, character error rate, numeric error, calibration-safe
aggregation, validation-only threshold selection, fail-closed policy and manifest metadata. The
repository contains neither an approved exam dataset nor evaluated model weights, so this sprint
does **not** publish an OCR success percentage, recommended production threshold or production-ready
model. EMNIST remains pretraining data and cannot establish end-to-end exam-paper accuracy.
