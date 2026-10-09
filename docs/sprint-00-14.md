# 00-14 — iOS API & Secure Session Foundation

## Scope

Sprint 00-14 replaces the unauthenticated iOS placeholder entry point with the
shared backend's real session boundary:

`Institution login → Keychain tokens → Authorized API → Automatic refresh`

## Delivered behavior

- Login uses the backend's institution code, e-mail and password contract.
- Access and refresh tokens are stored in Keychain rather than user defaults.
- Launch restores the current user when a saved session exists.
- One expired access token triggers one refresh-token rotation and request retry.
- Logout clears the secure token pair.
- Typed models cover the authenticated user, course offerings and exams.
- Server error envelopes are converted to user-readable login errors without
  exposing credentials or tokens.

The API client is transport-injected and covered by deterministic Swift tests.
