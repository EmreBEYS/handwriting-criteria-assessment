# 00-07 — Questions & Program Outcome Mapping

## Scope

Sprint 00-07 completes exam configuration before scan processing begins:

`Draft exam → Dynamic questions → Program outcome weights → Active exam`

Questions are rows rather than fixed columns, so each exam can define its own
question count, order and maximum scores. Every question maps to one or more
active outcomes from the course offering's program.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/course-offerings/{id}/program-outcomes` | List selectable active outcomes |
| `POST/GET` | `/api/v1/exams/{id}/questions` | Create or list dynamic questions |
| `GET/PATCH/DELETE` | `/api/v1/questions/{id}` | Manage one draft-exam question |
| `PUT` | `/api/v1/questions/{id}/program-outcomes` | Atomically replace outcome weights |
| `POST` | `/api/v1/exams/{id}/activate` | Validate and activate the exam |

## Validation and lifecycle

- Question numbers and display orders are unique within an exam.
- A question maximum is positive and cannot exceed the exam total.
- Outcome identifiers must be active and belong to the offering's program.
- Each question's outcome weights are unique, positive and total exactly `1`.
- Activation requires at least one question, question maximums totaling the
  exam score, and complete outcome mappings for every question.
- Exam and question configuration becomes immutable after activation.

Program outcome catalog administration remains outside this sprint; this API
exposes the active outcomes already defined for the selected program.
