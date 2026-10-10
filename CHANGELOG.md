# Changelog

## 1.0.0 — 2026-10-10

- Completed the authenticated academic structure, exam, question/PÇ and roster APIs.
- Added idempotent private scan upload, asynchronous OCR worker and versioned layout extraction.
- Added mandatory instructor review, atomic confirmation, audit events and duplicate-paper guards.
- Added confirmed-score PÇ analysis and private Excel export.
- Added the native iOS login, secure session, capture, resilient retry, review and PÇ result flows.
- Added writer-disjoint OCR evaluation, calibration, aggregate error analysis and fail-closed threshold
  selection without publishing fabricated accuracy.
- Added server-side refresh rotation/logout revocation, production security gates, upload signature and
  queue-abuse checks, CI, system tests and a bounded performance smoke tool.
- Added deployment, KVKK, academic evaluation, demo and release-gate documentation.

Version 1.0.0 is the code-complete academic release candidate. Physical iPhone validation, approved
institutional data, an evaluated model bundle and production infrastructure sign-off remain external
release gates and are not claimed by this tag candidate.
