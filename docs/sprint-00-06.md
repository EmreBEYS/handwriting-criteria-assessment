# 00-06 — Exam Definition

## Scope

Sprint 00-06 adds the authenticated exam-definition flow on top of the course
offerings delivered in 00-05. An instructor can only see and use offerings to
which they are assigned.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/course-offerings` | List the current instructor's offerings |
| `GET` | `/api/v1/course-offerings/{id}` | Read one assigned offering |
| `POST/GET` | `/api/v1/course-offerings/{id}/exams` | Create or list exams |
| `GET/PATCH/DELETE` | `/api/v1/exams/{id}` | Read, edit or delete a draft exam |

Exam types are `midterm`, `final` and `makeup`. New exams always start as
`draft`; lifecycle transitions are intentionally deferred until questions can
be validated. A makeup may reference a final from the same course offering.

Unassigned and cross-institution resources are returned as not found. Exam
type, course offering and creator are immutable after creation, and only draft
exams can be edited or removed.
