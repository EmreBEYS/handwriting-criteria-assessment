# v1.0 Release Checklist

## Completed in repository

- [x] API, ML and iOS package lint/tests pass.
- [x] Full synthetic scan → review → confirmation → PÇ → Excel system test passes.
- [x] Migrations 001–004 and rollback policy are documented.
- [x] Production config fails closed on TLS/object-storage/JWT/CORS requirements.
- [x] Refresh replay/logout, tenant access, media spoofing and queue limits are tested.
- [x] OCR evaluation reports aggregate metrics without labels, paths or writer identities.
- [x] README, changelog, deployment, demo, security and academic evaluation documents exist.

## External gates before production or an empirical OCR claim

- [ ] Physical iPhone camera, permission, termination, storage pressure and network handover verified.
- [ ] PostgreSQL 15+ migrations and concurrent refresh/confirmation locking verified in staging.
- [ ] Private object storage encryption, lifecycle deletion and restore evidence approved.
- [ ] KVKK lawful basis, notice, roles, retention period and incident process approved in writing.
- [ ] Writer-disjoint approved dataset evaluated; model/manifest hashes and metrics recorded.
- [ ] Target-environment API latency and sustained worker throughput measured.
- [ ] Academic supervisor/product owner approves the demo and remaining limitations.

Unchecked gates are blockers for production deployment or accuracy claims, not hidden successes.
