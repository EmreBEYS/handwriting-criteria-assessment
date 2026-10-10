# Deployment Guide

## Components

Deploy the API and worker as separate processes from the same immutable source/image. Both require
PostgreSQL, the private S3-compatible bucket, the versioned layout file and—only after approval—the
same evaluated model bundle. The iOS app communicates only with the HTTPS API.

## Database

Back up the target database, then apply `database/migrations/001_...sql` through
`004_refresh_sessions.sql` in numeric order with `ON_ERROR_STOP=1`. Do not edit a migration that has
already been applied. Verify `scan_jobs`, `exam_papers`, `paper_answers`, `audit_events` and
`refresh_sessions` before starting traffic.

## Runtime configuration

Start from `.env.example` but load real values from a secret manager. Production startup requires:

- `HCA_APP_ENV=production`
- `HCA_REQUIRE_HTTPS=true`
- a random `HCA_JWT_SECRET_KEY` of at least 32 characters
- HTTPS-only `HCA_CORS_ALLOWED_ORIGINS`
- `HCA_OBJECT_STORAGE_USE_SSL=true` and private bucket credentials
- `HCA_DATABASE_URL` for the least-privileged application role
- `HCA_MODEL_PATH` only for a model whose exact hash has an approved Sprint 00-17 report
- `FORWARDED_ALLOW_IPS` restricted to the trusted TLS proxy address/range

Do not copy `.env`, model weights or exam data into the container image or Git repository. Mount the
approved model read-only. Keep `HCA_MODEL_PATH` empty when no approved model exists; scans then fail
openly with `MODEL_NOT_CONFIGURED` rather than using an unverified fallback.

## Processes

API:

```bash
uvicorn app.main:app --app-dir api --host 0.0.0.0 --port 8000 --proxy-headers
```

Worker (run continuously under the platform's process supervisor):

```bash
python -m app.worker
```

The included Docker image starts the API as an unprivileged user. Run the same image with
`python -m app.worker` for worker instances. The public load balancer must perform TLS termination,
forward the original HTTPS scheme and expose only the API port.

## Release verification and rollback

1. Check `/health/live` and `/health/ready` over HTTPS.
2. Run Python/Swift tests and the target-environment performance smoke command.
3. Complete one synthetic or institutionally approved end-to-end paper and verify the audit event,
   PÇ result and Excel workbook.
4. Verify another instructor/institution cannot access those resources.
5. Confirm object encryption, backup restore and retention deletion with platform evidence.

For rollback, stop new uploads, retain the database backup and object-storage snapshot, redeploy the
previous application image, and roll the database back only with a separately reviewed compensating
migration. Never delete confirmed grades or audit events to force a rollback.
