# API Contracts

Contracts are versioned independently under `v1/`. The response envelope is
criterion-independent: identifiers and labels are opaque strings, so no domain
criterion or model class is fixed by this scaffold.

`POST /v1/analyses` currently accepts one `multipart/form-data` `image` field,
documented by `analysis-request.schema.json`. Until a model and criteria are
approved, a valid image intentionally returns
`503 MODEL_NOT_CONFIGURED`; this prevents placeholder logic from becoming an
accidental product decision.
