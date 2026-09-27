# API

The FastAPI service lives in `api/app`. It provides a health endpoint, multipart
image validation, stable error envelopes with request IDs, and OpenAPI docs.

Analysis intentionally stops with `MODEL_NOT_CONFIGURED`: transport can be
tested without encoding a placeholder classifier before approval.
