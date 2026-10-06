BEGIN;

CREATE TABLE academic_years (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    start_year smallint NOT NULL CHECK (start_year BETWEEN 2000 AND 2200),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, start_year),
    UNIQUE (id, institution_id)
);

INSERT INTO academic_years (institution_id, start_year)
SELECT DISTINCT institution_id, start_year
FROM academic_terms;

ALTER TABLE academic_terms ADD COLUMN academic_year_id uuid;

UPDATE academic_terms AS academic_term
SET academic_year_id = academic_year.id
FROM academic_years AS academic_year
WHERE academic_year.institution_id = academic_term.institution_id
  AND academic_year.start_year = academic_term.start_year;

ALTER TABLE academic_terms
    ALTER COLUMN academic_year_id SET NOT NULL,
    ADD CONSTRAINT academic_terms_academic_year_fk
        FOREIGN KEY (academic_year_id, institution_id)
        REFERENCES academic_years(id, institution_id)
        ON DELETE CASCADE,
    ADD CONSTRAINT academic_terms_year_season_unique
        UNIQUE (academic_year_id, season);

CREATE INDEX idx_academic_terms_year ON academic_terms (academic_year_id);

COMMIT;
