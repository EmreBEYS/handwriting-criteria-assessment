# 00-20 — Final Release, Documentation & Academic Demo

## Delivered

- Aligned API, Python package and ML package at version `1.0.0` with a consistency test.
- Connected the worker to an explicitly configured evaluated digit-model checkpoint; missing or
  unreadable weights retain the fail-closed `MODEL_NOT_CONFIGURED` behavior.
- Kept course text as an optional model capability. A digit-only model marks
  `COURSE_NOT_MACHINE_VERIFIED` and preserves mandatory instructor review.
- Added an unprivileged production container, deployment/rollback guide, changelog, security policy,
  academic demo runbook, evaluation plan and release checklist.
- Recorded the exact local test evidence and unavailable-environment limits in
  `verification-2026-10-10.md`.
- Marked every physical-device, approved-dataset, staging PostgreSQL, object-storage and production
  performance item as an external gate rather than fabricating completion evidence.

## Release interpretation

Sprint 00-20 closes the planned implementation roadmap and produces the v1.0.0 academic release
candidate. It does not convert unperformed external validation into a success claim. Production
deployment and empirical OCR claims remain blocked until every applicable unchecked item in
`release-checklist.md` has evidence and approval.
