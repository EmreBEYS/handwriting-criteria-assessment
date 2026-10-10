# 00-19 — System Testing, Security & Performance

## Scope

Sprint 00-19 hardens the completed workflow and makes release checks repeatable:

`Authentication → upload → OCR review → atomic confirmation → PÇ analysis → Excel export`

## Security changes

- Production configuration now fails startup unless HTTPS enforcement, encrypted object-storage
  transport, HTTPS CORS origins and a strong JWT secret are configured.
- API responses set no-store, content-type, framing, referrer, content-security and permissions
  headers; HTTPS responses also set HSTS.
- Uploads verify PNG, JPEG, HEIC and HEIF signatures instead of trusting multipart media types.
- Per-user queued/processing scan limits bound storage and worker queue abuse while idempotent retries
  still return the existing job.
- Refresh token identifiers are persisted. Rotation revokes the previous refresh session, replay is
  rejected, and logout revokes the current server-side session before clearing Keychain data.
- Migration `004_refresh_sessions.sql` adds the server-side refresh-session state.

## Verification

- The system test crosses upload, worker prediction, instructor correction, atomic save, PÇ analysis,
  Excel creation and authorized download in one scenario.
- Security tests cover response headers, optional HTTPS enforcement, production configuration,
  media spoofing, queue limiting, tenant boundaries, refresh replay and logout revocation.
- GitHub Actions runs Python lint/tests (including ML dependencies) and Swift package tests.
- `tools/performance_smoke.py` runs a bounded concurrent HTTP check, reports errors plus p50/p95/max,
  and fails when the configured p95 target is exceeded.

Example against a deployed HTTPS environment:

```bash
python tools/performance_smoke.py \
  --base-url https://api.example.edu \
  --path /health/live \
  --requests 100 \
  --concurrency 10 \
  --p95-target-ms 500
```

For an authenticated endpoint, put the short-lived token in an environment variable and pass only
its variable name with `--access-token-env`; the tool never prints the token.

## Limits

Repository tests use SQLite and in-memory object storage. They do not establish production
PostgreSQL locking behavior, S3 encryption, internet latency, sustained OCR throughput or a service
level objective. The smoke tool must be run in the target environment before release; no production
latency result is claimed here.
