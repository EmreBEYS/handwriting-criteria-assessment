# Security Policy

## Reporting

Do not open a public issue containing credentials, student data, exam images or an exploitable
security detail. Use GitHub's private security advisory flow for this repository and include only
synthetic reproduction data.

## Supported release

Security fixes target the current `1.0.x` line. Secrets and model/data artifacts are not distributed
with source releases.

## Deployment baseline

- Terminate trusted TLS before the API and set `HCA_REQUIRE_HTTPS=true`.
- Use a strong secret-manager JWT key and TLS-enabled private object storage.
- Apply every numbered PostgreSQL migration before starting API or worker processes.
- Restrict database, object-storage and model-file access to the API/worker service identities.
- Keep logs free of tokens, names, student numbers and image content.
- Back up, restore-test, retain and delete data under the institution's approved KVKK policy.
- Run the release checklist and rotate any credential suspected of exposure.
