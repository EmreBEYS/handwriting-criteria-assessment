# Sprint 00-01 — Foundation

## Goal

Create a clean, runnable foundation without guessing assessment criteria, label
classes, training data, or model architecture before the supervisor meeting.

## Delivered scope

- Audited and refined the repository structure.
- Added a Python 3.11+ project with separate API and reusable ML packages.
- Added a FastAPI health endpoint, upload validation boundary, stable errors,
  and OpenAPI documentation.
- Added versioned, criterion-independent JSON response contracts.
- Added an iOS SwiftUI package with Home → Capture/Upload → Analysis → Results
  navigation and placeholder-only screens.
- Added environment examples, ignore rules, setup guides, and smoke tests.
- Documented deferred decisions and supervisor questions.

## Explicitly out of scope

- Any criterion, label, score meaning, model class, preprocessing rule, training
  pipeline, dataset collection, or inference implementation
- Production camera/photo-library integration, networking, persistence,
  authentication, analytics, or polished visual design
- All Android implementation

## Closure criteria

Sprint 00-01 is closed when:

- A fresh Python environment installs the declared dependencies.
- Python lint and smoke tests pass.
- The API reports healthy with `model_ready: false` and refuses inference with
  an explicit `MODEL_NOT_CONFIGURED` response.
- The Swift package builds/tests and the four-screen flow is navigable.
- No data, model artifacts, secrets, or generated build files are tracked.
- Deferred supervisor decisions are visible in `docs/open-questions.md`.

After the meeting, record decisions before the next implementation sprint and
revise contracts only through a reviewed, versioned change.
