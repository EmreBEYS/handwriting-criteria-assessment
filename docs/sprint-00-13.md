# 00-13 — PÇ Analysis & Excel Export

## Scope

Sprint 00-13 converts instructor-confirmed scores into reproducible course
assessment results:

`Confirmed papers → Question statistics → PÇ weighted analysis → Excel report`

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/exams/{id}/po-analysis` | Return question and PÇ achievement statistics |
| `POST` | `/api/v1/exams/{id}/exports` | Generate a private, seven-day Excel export |
| `GET` | `/api/v1/exports/{id}/download` | Download a ready export as `.xlsx` |

## Calculation and report rules

- Processing, review and rejected papers never enter the analysis.
- Question averages and success percentages use final instructor-approved scores.
- Each answer contributes `final score × PÇ weight`; its maximum contribution is
  `question maximum × PÇ weight`.
- Percentages are rounded only in the response/report presentation layer.
- The workbook contains **Öğrenci Puanları**, **Soru Analizi**, **PÇ Analizi**
  and **Metadata** sheets. Metadata records the generation time, academic year,
  term, course, section, exam and report author.
- Export objects use private encrypted storage through the existing storage
  adapter. Object keys are never returned, downloads require authentication and
  exports expire after seven days.
