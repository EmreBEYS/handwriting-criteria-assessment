# 00-18 — iOS Production Readiness & Resilient Scan Queue

## Scope

Android is outside the agreed product scope. Sprint 00-18 hardens the native iOS path instead:

`Capture → protected local pending item → idempotent retry → server queue → human review`

## Delivered behavior

- A captured paper is persisted immediately before upload with iOS complete file protection.
- Pending scan files are excluded from device backup and remain inside application support storage.
- A failed upload keeps its original `client_request_id`; reopening the same exam restores the
  oldest pending scan and retries idempotently.
- Selecting a replacement image removes the superseded pending item and creates a new request ID.
- Successful upload deletes the local pending copy. Logout purges every pending paper so a later
  account cannot inherit another instructor's capture.
- The device still sends images only through the authenticated API. It never receives PostgreSQL or
  object-storage credentials.
- File and in-memory store tests cover restore, exam isolation, removal and logout-ready purge.

## Operational limits

This is a durable retry mechanism, not unattended background synchronization. The instructor must
reopen the exam and tap retry after connectivity returns. iOS Data Protection behavior, low-storage
handling, process termination during a write and actual network handover still require the physical
device protocol in Sprint 00-16. No real-device result is claimed by repository tests.
