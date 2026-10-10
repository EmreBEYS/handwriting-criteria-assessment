# Academic Demo Runbook

## Safe preparation

- Use synthetic students and exam sheets unless institutional approval explicitly permits real data.
- Configure the iPhone, HTTPS API, PostgreSQL, private object storage and worker on an isolated demo
  environment. Never use production credentials in slides or terminal history.
- If an approved OCR bundle is unavailable, state this before the demo and show the explicit
  `MODEL_NOT_CONFIGURED` path plus repository system tests. Do not substitute invented accuracy.

## 10-minute flow

1. Sign in on iOS and show that only the assigned course/exam appears.
2. Capture a synthetic exam paper. Briefly disable connectivity, retry, and show that the same
   request produces one scan job.
3. Run/observe the worker. Open the review screen, explain confidence warnings and correct one score.
4. Confirm the paper and show “Okundu ve Kaydedildi” with the authoritative total.
5. Show the updated PÇ percentage and confirmed-paper count.
6. Generate/download the Excel report and compare its score/PÇ values with the confirmed screen.
7. Show the audit event, private object key (not the image), model version and request correlation ID.
8. End with the limitations: human confirmation is mandatory; no SIS auto-submit; empirical OCR and
   physical-device results must come from approved protocols.

## Recovery paths

- Network failure: reopen the same exam and retry the protected pending scan.
- Model unavailable: show the explicit failed job and do not claim OCR success.
- Ambiguous identity or score: select the roster student/correct score and record a reason.
- Export unavailable: retain the confirmed database result and retry export separately.
