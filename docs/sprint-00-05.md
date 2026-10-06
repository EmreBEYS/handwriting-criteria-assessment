# 00-05 — Course & Academic Structure

## Scope

Sprint 00-05 implements the authenticated academic selection flow:

`Instructor → Academic year → Semester → Course`

The existing database design remains intact. `academic_terms` continues to be
the physical semester table and `course_offerings` remains the relationship
between a course, term, program and section. Migration `002_academic_years.sql`
adds a persistent parent for academic years and backfills it from existing term
rows.

## API

All endpoints require an access token and scope every lookup to the current
user's institution.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST/GET` | `/api/v1/academic-years` | Create or list academic years |
| `GET/PATCH/DELETE` | `/api/v1/academic-years/{id}` | Read, update or delete one year |
| `POST/GET` | `/api/v1/semesters` | Create or list semesters |
| `GET/PATCH/DELETE` | `/api/v1/semesters/{id}` | Read, update or delete one semester |
| `POST/GET` | `/api/v1/courses` | Create or list courses |
| `GET/PATCH/DELETE` | `/api/v1/courses/{id}` | Read, update or delete one course |
| `POST` | `/api/v1/course-offerings` | Open a course in a semester and assign its creator |

`GET /api/v1/courses` accepts `academic_year_id` and `semester_id` query
parameters and returns the authenticated instructor's assigned offerings when
either filter is present. `GET /api/v1/semesters` accepts `academic_year_id`.

## Validation and conflicts

- Academic years are limited to `2000..2200` and formatted as `2026–2027`.
- A year can contain one `fall` and one `spring` semester.
- Semester end dates must be later than start dates.
- Course codes are normalized to uppercase and unique inside an institution.
- Cross-institution identifiers are returned as not found.
- Years, semesters and courses with course offerings cannot be deleted.
- Creating a course offering assigns the authenticated instructor as `owner`.

Exam types, questions, program outcomes and question–outcome mappings remain
outside this sprint.
