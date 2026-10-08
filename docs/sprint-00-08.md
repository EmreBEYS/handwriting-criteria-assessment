# 00-08 — Student Roster & Enrollment

## Scope

Sprint 00-08 adds the student roster required before exam papers can be
matched and confirmed:

`Institution student → Course-offering enrollment → Active roster`

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST/GET` | `/api/v1/students` | Create or list institution students |
| `GET/PATCH` | `/api/v1/students/{id}` | Read, edit or deactivate a student |
| `POST/GET` | `/api/v1/course-offerings/{id}/enrollments` | Add or list roster entries |
| `DELETE` | `/api/v1/course-offerings/{id}/enrollments/{student_id}` | Deactivate an enrollment |

## Validation and access

- Student numbers are trimmed, normalized to uppercase and unique per institution.
- Every lookup is limited to the authenticated user's institution.
- Only instructors assigned to a course offering can view or change its roster.
- Inactive students cannot be enrolled and are omitted from active rosters.
- Removing a roster entry deactivates it instead of deleting academic history.

Bulk import is intentionally deferred until the institution's CSV/Excel format
has been confirmed.
