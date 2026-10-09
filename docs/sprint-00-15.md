# 00-15 — iOS Scan Queue & Human Review

## Scope

Sprint 00-15 connects the authenticated iOS application to the completed paper
assessment workflow:

`Course/exam selection → Camera/photo → Upload → Poll → Review → Saved`

## Delivered behavior

- The home screen loads assigned course offerings and active exams from the API.
- Course responses include readable course and academic-term labels for mobile clients.
- A paper can be captured with the iPhone camera or selected from Photos, normalized
  to JPEG and uploaded with a stable client request ID.
- The app polls queued/processing scans until review data or an explicit failure arrives.
- Review shows the predicted student, machine-readable warnings, every dynamic
  question score and its configured maximum.
- The instructor selects an active roster student, corrects scores, optionally
  records a reason and submits the atomic Sprint 00-12 confirmation contract.
- Success renders the authoritative total and explicit “Okundu ve Kaydedildi” state.
- Multipart upload construction and navigation remain covered by Swift tests.

## Visual language

The iOS flow uses an İnönü mobile-inspired visual system without coupling the
product to unrelated campus-app content: a near-black background, cyan/turquoise
gradient accents, rounded elevated cards, compact status pills and SF Symbols.
The same system covers login, home/exam selection, capture, review, confirmation
and the instructor profile. Text and state indicators retain sufficient contrast
and never rely on color alone.

Set `HCA_API_BASE_URL` in the Xcode scheme for the reachable backend address. A
device build must also provide `NSCameraUsageDescription` in its application
target settings before camera capture is used.
