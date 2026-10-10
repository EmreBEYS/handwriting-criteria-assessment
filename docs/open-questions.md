# Questions for the Supervisor Meeting

No criterion, label, or model class should be implemented until these points are
resolved and recorded.

## Assessment definition

- What exact criteria are academically in scope, and what is the operational
  definition of each?
- What label values are allowed, and what does a probability mean for each?
- What claims and interpretations are explicitly prohibited?
- How will ground truth be established, and who is qualified to annotate it?
- How should ambiguous, unreadable, multilingual, or out-of-scope samples be handled?

## Data and evaluation

- Is there an approved dataset, or may new samples be collected?
- What consent, anonymization, storage, retention, access, and deletion rules apply?
- Which participant groups and capture conditions must be represented?
- Which metrics and minimum acceptance thresholds will define success?
- How will participant-level train/validation/test separation be enforced?

## Product and deployment

- Is inference server-side, on-device, or hybrid?
- Must the iOS app work offline, and what iOS/device versions are required?
- What image formats, resolution limits, latency target, and retry behavior are expected?
- Is authentication required, and may images or results be persisted?
- What must the demo include, and what is the final delivery date/checkpoint?

## Team boundary

- Android is outside the agreed product scope. Contract changes, integration
  testing and release coordination apply to the iOS client and shared backend.
