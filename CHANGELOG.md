# Changelog

## Unreleased — Sprint 00-22

- Integrated the attributed `digit-crnn-v3` ONNX handwritten numeric model behind a pinned ONNX Runtime adapter.
- Ported the source Rust/Python preprocessing and greedy CTC decoding contract to Swift.
- Added the calibrated `0.99` review gate, correction/blank/total-mismatch review flags and a fail-safe Apple Vision fallback.
- Added 15-fixture preprocessing/inference parity and regression benchmark tests while keeping all Sprint 00-21 tests passing.
- Documented the source commit, model hash, measured limits, verbal permission and unresolved upstream/data license gates.

## Sprint 00-21

- Replaced the active account/API/PostgreSQL iOS flow with an on-device document scanning flow.
- Added fixed-template Vision OCR for student name, variable question scores and written total.
- Added editable question–PÇ mappings and accessible traffic-light confidence indicators.
- Added multi-page serial scanning without a review screen and cumulative Excel output.
- Added native `.xlsx` export with green/yellow/red confidence-colored cells.
- Moved the 00-20 server-oriented implementation to legacy/reference status without claiming Android work.

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
