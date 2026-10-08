BEGIN;

ALTER TABLE exam_papers
    ADD COLUMN predicted_student_name text,
    ADD COLUMN student_name_confidence numeric(5,4)
        CHECK (student_name_confidence BETWEEN 0 AND 1),
    ADD COLUMN predicted_course_text text,
    ADD COLUMN course_confidence numeric(5,4)
        CHECK (course_confidence BETWEEN 0 AND 1),
    ADD COLUMN review_reasons jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMIT;
