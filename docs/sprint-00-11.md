# 00-11 — Handwriting Inference Worker

## Scope

Sprint 00-11 connects queued scans to the exam-paper prediction model:

`Queued scan → Layout regions → OCR provider → Roster and course checks → Review result`

## Worker behavior

- Claims one queued job and records attempt, timing and model version metadata.
- Reads the private image from object storage and applies the versioned 00-10 layout.
- Requests predictions for printed course identity, handwritten student number
  and every dynamic score cell. The name crop is not required for automation.
- Matches the student against the active course roster. It accepts an exact number or a
  unique roster candidate at edit distance one; ambiguous candidates require review.
- Rejects unparsable, negative and above-maximum score predictions.
- Returns the paper's predicted total only when every question score was recognized.
- Stores predictions separately from final scores and always sends a produced
  paper to human review.
- Exposes predictions through the existing authenticated scan-status endpoint.

Image warnings, course mismatch, identity uncertainty, duplicate student paper,
invalid scores and low-confidence scores are retained as machine-readable review
reasons. Missing model weights fail explicitly with `MODEL_NOT_CONFIGURED`.

## Model and dataset boundary

The worker depends on a small `HandwritingRecognizer` interface so evaluated
model weights can be installed without coupling the API to one ML framework.
The repository contains no fabricated production model. The dataset manifest
validator enforces anonymous writer-level train/validation/test separation; see
[`handwriting-dataset-protocol.md`](handwriting-dataset-protocol.md).

Human correction and atomic confirmation remain Sprint 00-12.
