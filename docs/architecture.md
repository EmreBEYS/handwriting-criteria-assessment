# Architecture Decisions

## Confirmed in Sprint 00-01

- The user-owned mobile client is iOS with SwiftUI; Android is a separate
  teammate-owned workstream.
- Python 3.11+ is the shared runtime for API and ML tooling.
- FastAPI provides a thin, versioned transport boundary.
- API contracts live under `contracts/v1` and do not enumerate criteria or
  label classes.
- Reusable ML code belongs in `ml/src/handwriting_ml`; notebooks are exploratory.
- Data, model files, environments, secrets, and local build output stay outside Git.

## Deliberately deferred

Inference location, model architecture and format, preprocessing, storage,
authentication, supported devices, latency target, offline behavior, and model
updates require supervisor decisions. See `docs/open-questions.md`.
