# 00-12 — Human Review & Atomic Confirmation

## Scope

Sprint 00-12 turns model predictions into instructor-approved assessment data:

`Needs review → Student/score corrections → Atomic confirmation → Saved`

## API

`POST /api/v1/papers/{paper_id}/confirm` accepts the enrolled student and one
final score for every configured question. A successful response contains the
explicit `saved` state, the authoritative total and `saved_at` timestamp.

## Integrity and audit rules

- Only an instructor assigned to the exam can confirm its paper.
- The selected student must be active in the course roster.
- Every question must occur exactly once and remain within its configured maximum.
- Student assignment, final answers, paper state and scan state are committed in
  one database transaction; validation failure leaves all final scores unchanged.
- A student cannot have two active/confirmed papers for the same exam.
- Prediction-to-final corrections, student reassignment, actor and reason are
  retained in an audit event. Model predictions remain unchanged.
- Confirmed papers cannot be confirmed a second time through this endpoint.
