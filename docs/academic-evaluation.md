# Academic Evaluation Plan

This document separates implemented evidence from measurements that require approved external data.

| Evidence | Repository status | Required final evidence |
|---|---|---|
| Functional workflow | Automated synthetic system test | Physical-iPhone approved-data run |
| Student-number exact match | Evaluator implemented | Held-out writer result: not measured |
| Score exact match / numeric MAE | Evaluator implemented | Held-out writer result: not measured |
| Confidence calibration / review rate | Evaluator implemented | Approved validation/test report: not measured |
| API p95 latency | Smoke gate implemented | Target environment result: not measured |
| OCR throughput | Async worker implemented | Sustained target-environment result: not measured |
| Tenant isolation and atomic save | Automated tests pass | PostgreSQL staging verification |
| KVKK retention/deletion | Procedure documented | Institution-approved policy and execution evidence |

The final thesis/report must record dataset provenance, lawful basis, writer-disjoint sample counts,
model and manifest hashes, threshold-selection rule, every metric with confidence intervals where
appropriate, capture-condition slices and all excluded/unreadable samples. EMNIST accuracy cannot be
reported as end-to-end exam accuracy.

No model may be described as production-ready until the approved test split is evaluated once after
model/threshold freeze, high-confidence errors are reviewed, physical-device behavior is verified and
the responsible academic/institutional reviewers sign off. Regardless of metrics, instructor review
and explicit confirmation remain mandatory.
