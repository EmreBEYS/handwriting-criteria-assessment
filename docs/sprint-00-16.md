# 00-16 — iOS End-to-End Integration & Testing

## Scope

Sprint 00-16 closes the implemented iOS application loop:

`Device capture → authenticated upload → PostgreSQL-backed review → confirmation → PÇ results`

## Delivered behavior

- Upload retries keep the same `client_request_id`, so a timeout or repeated tap cannot create a
  second scan job for the same captured paper.
- The existing authenticated API remains the only path to PostgreSQL; the device never connects to
  the database or object store directly.
- Instructor review and atomic confirmation remain mandatory for every model result.
- After confirmation, iOS reads the authorized exam PÇ analysis and shows the current confirmed
  paper count and outcome percentages. A failed analysis request can be retried without repeating
  confirmation.
- API transport tests cover multipart idempotency and the PÇ analysis contract.

## Real-device verification protocol

The repository has no physical iPhone or production backend credentials. Before release, run this
checklist on a non-production course containing synthetic or institutionally approved data:

1. Configure an HTTPS `HCA_API_BASE_URL` reachable by the phone and add
   `NSCameraUsageDescription` to the app target.
2. Sign in, select the assigned course and an active exam, capture a complete paper in portrait and
   upload it.
3. Interrupt the network during upload, retry, and verify that only one `scan_jobs` row exists for
   the request ID.
4. Run the worker, verify the predicted student and every dynamic score, correct at least one value,
   give a reason, and confirm.
5. Verify one confirmed paper and its answers in PostgreSQL, the corresponding audit event, and the
   updated PÇ result on the phone.
6. Confirm that another institution/instructor cannot read the scan, paper, analysis, or export.
7. Remove the test image and records according to the approved KVKK retention procedure.

## Limitations

Simulator/package tests do not prove camera permission behavior, lighting/focus quality, phone-to-
backend routing, TLS trust, object-storage encryption, or a live PostgreSQL transaction. Those items
remain explicitly gated by the real-device protocol above; no device-test result is claimed here.
