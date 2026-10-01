BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TYPE user_role AS ENUM ('admin', 'instructor');
CREATE TYPE term_season AS ENUM ('fall', 'spring');
CREATE TYPE instructor_role AS ENUM ('owner', 'grader', 'viewer');
CREATE TYPE exam_type AS ENUM ('midterm', 'final', 'makeup');
CREATE TYPE exam_status AS ENUM ('draft', 'active', 'closed', 'archived');
CREATE TYPE scan_status AS ENUM (
    'queued', 'processing', 'needs_review', 'saved', 'failed', 'cancelled'
);
CREATE TYPE paper_status AS ENUM (
    'processing', 'needs_review', 'confirmed', 'rejected'
);
CREATE TYPE export_status AS ENUM ('queued', 'processing', 'ready', 'failed', 'expired');

CREATE TABLE institutions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (btrim(name) <> ''),
    code text NOT NULL UNIQUE CHECK (btrim(code) <> ''),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    email citext NOT NULL,
    password_hash text NOT NULL,
    first_name text NOT NULL CHECK (btrim(first_name) <> ''),
    last_name text NOT NULL CHECK (btrim(last_name) <> ''),
    role user_role NOT NULL DEFAULT 'instructor',
    is_active boolean NOT NULL DEFAULT true,
    last_login_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, email),
    UNIQUE (id, institution_id)
);

CREATE TABLE academic_terms (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    start_year smallint NOT NULL CHECK (start_year BETWEEN 2000 AND 2200),
    season term_season NOT NULL,
    starts_on date,
    ends_on date,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_on IS NULL OR starts_on IS NULL OR ends_on > starts_on),
    UNIQUE (institution_id, start_year, season),
    UNIQUE (id, institution_id)
);

CREATE TABLE programs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    code text NOT NULL CHECK (btrim(code) <> ''),
    name text NOT NULL CHECK (btrim(name) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, code),
    UNIQUE (id, institution_id)
);

CREATE TABLE program_outcomes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id uuid NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    code text NOT NULL CHECK (btrim(code) <> ''),
    description text NOT NULL CHECK (btrim(description) <> ''),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (program_id, code)
);

CREATE TABLE courses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    code text NOT NULL CHECK (btrim(code) <> ''),
    name text NOT NULL CHECK (btrim(name) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, code),
    UNIQUE (id, institution_id)
);

CREATE TABLE course_offerings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL,
    academic_term_id uuid NOT NULL,
    program_id uuid NOT NULL,
    course_id uuid NOT NULL,
    section_code text NOT NULL DEFAULT '1' CHECK (btrim(section_code) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (academic_term_id, institution_id)
        REFERENCES academic_terms(id, institution_id),
    FOREIGN KEY (program_id, institution_id)
        REFERENCES programs(id, institution_id),
    FOREIGN KEY (course_id, institution_id)
        REFERENCES courses(id, institution_id),
    UNIQUE (academic_term_id, program_id, course_id, section_code),
    UNIQUE (id, institution_id)
);

CREATE TABLE course_instructors (
    course_offering_id uuid NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id),
    role instructor_role NOT NULL DEFAULT 'grader',
    assigned_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (course_offering_id, user_id)
);

CREATE TABLE students (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES institutions(id),
    student_number text NOT NULL CHECK (btrim(student_number) <> ''),
    first_name text NOT NULL CHECK (btrim(first_name) <> ''),
    last_name text NOT NULL CHECK (btrim(last_name) <> ''),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, student_number),
    UNIQUE (id, institution_id)
);

CREATE TABLE enrollments (
    course_offering_id uuid NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    student_id uuid NOT NULL REFERENCES students(id),
    enrolled_at timestamptz NOT NULL DEFAULT now(),
    is_active boolean NOT NULL DEFAULT true,
    PRIMARY KEY (course_offering_id, student_id)
);

CREATE TABLE exams (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES course_offerings(id),
    type exam_type NOT NULL,
    title text NOT NULL CHECK (btrim(title) <> ''),
    total_score numeric(8,3) NOT NULL DEFAULT 100 CHECK (total_score > 0),
    status exam_status NOT NULL DEFAULT 'draft',
    held_at timestamptz,
    replaces_exam_id uuid REFERENCES exams(id),
    created_by uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (replaces_exam_id IS NULL OR replaces_exam_id <> id),
    UNIQUE (course_offering_id, type, title)
);

CREATE TABLE exam_questions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id uuid NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    question_number integer NOT NULL CHECK (question_number > 0),
    label text,
    max_score numeric(8,3) NOT NULL CHECK (max_score > 0),
    display_order integer NOT NULL CHECK (display_order > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (exam_id, question_number),
    UNIQUE (exam_id, display_order),
    UNIQUE (id, exam_id)
);

CREATE TABLE question_program_outcomes (
    exam_question_id uuid NOT NULL REFERENCES exam_questions(id) ON DELETE CASCADE,
    program_outcome_id uuid NOT NULL REFERENCES program_outcomes(id),
    weight numeric(7,6) NOT NULL CHECK (weight > 0 AND weight <= 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (exam_question_id, program_outcome_id)
);

CREATE TABLE scan_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id uuid NOT NULL REFERENCES exams(id),
    requested_by uuid NOT NULL REFERENCES users(id),
    client_request_id uuid NOT NULL,
    status scan_status NOT NULL DEFAULT 'queued',
    image_object_key text NOT NULL CHECK (btrim(image_object_key) <> ''),
    image_sha256 text CHECK (image_sha256 ~ '^[0-9a-f]{64}$'),
    model_version text,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    error_code text,
    error_message text,
    queued_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz,
    saved_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (requested_by, client_request_id),
    CHECK (saved_at IS NULL OR status = 'saved')
);

CREATE TABLE exam_papers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id uuid NOT NULL UNIQUE REFERENCES scan_jobs(id),
    exam_id uuid NOT NULL REFERENCES exams(id),
    student_id uuid REFERENCES students(id),
    predicted_student_number text,
    student_number_confidence numeric(5,4)
        CHECK (student_number_confidence BETWEEN 0 AND 1),
    status paper_status NOT NULL DEFAULT 'processing',
    confirmed_by uuid REFERENCES users(id),
    confirmed_at timestamptz,
    rejection_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        status <> 'confirmed'
        OR (student_id IS NOT NULL AND confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)
    )
);

CREATE TABLE paper_answers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_paper_id uuid NOT NULL REFERENCES exam_papers(id) ON DELETE CASCADE,
    exam_question_id uuid NOT NULL REFERENCES exam_questions(id),
    predicted_score numeric(8,3) CHECK (predicted_score >= 0),
    prediction_confidence numeric(5,4)
        CHECK (prediction_confidence BETWEEN 0 AND 1),
    final_score numeric(8,3) CHECK (final_score >= 0),
    requires_review boolean NOT NULL DEFAULT true,
    reviewed_by uuid REFERENCES users(id),
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (exam_paper_id, exam_question_id)
);

CREATE TABLE export_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id uuid NOT NULL REFERENCES exams(id),
    requested_by uuid NOT NULL REFERENCES users(id),
    status export_status NOT NULL DEFAULT 'queued',
    object_key text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    expires_at timestamptz
);

CREATE TABLE audit_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    institution_id uuid NOT NULL REFERENCES institutions(id),
    actor_user_id uuid REFERENCES users(id),
    event_type text NOT NULL CHECK (btrim(event_type) <> ''),
    entity_type text NOT NULL CHECK (btrim(entity_type) <> ''),
    entity_id uuid,
    correlation_id uuid,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_institution_active ON users (institution_id, is_active);
CREATE INDEX idx_offerings_term ON course_offerings (academic_term_id);
CREATE INDEX idx_course_instructors_user ON course_instructors (user_id);
CREATE INDEX idx_enrollments_student ON enrollments (student_id);
CREATE INDEX idx_exams_offering ON exams (course_offering_id, status);
CREATE INDEX idx_scan_jobs_exam_status ON scan_jobs (exam_id, status, queued_at);
CREATE INDEX idx_exam_papers_exam_status ON exam_papers (exam_id, status);
CREATE UNIQUE INDEX uq_active_paper_per_exam_student
    ON exam_papers (exam_id, student_id)
    WHERE student_id IS NOT NULL
      AND status IN ('processing', 'needs_review', 'confirmed');
CREATE INDEX idx_audit_entity
    ON audit_events (entity_type, entity_id, occurred_at DESC);
CREATE INDEX idx_audit_institution_time
    ON audit_events (institution_id, occurred_at DESC);

CREATE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_set_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER programs_set_updated_at BEFORE UPDATE ON programs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER program_outcomes_set_updated_at BEFORE UPDATE ON program_outcomes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER courses_set_updated_at BEFORE UPDATE ON courses
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER course_offerings_set_updated_at BEFORE UPDATE ON course_offerings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER students_set_updated_at BEFORE UPDATE ON students
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER exams_set_updated_at BEFORE UPDATE ON exams
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER exam_questions_set_updated_at BEFORE UPDATE ON exam_questions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER scan_jobs_set_updated_at BEFORE UPDATE ON scan_jobs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER exam_papers_set_updated_at BEFORE UPDATE ON exam_papers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER paper_answers_set_updated_at BEFORE UPDATE ON paper_answers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE FUNCTION validate_question_po_weight_sum()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    new_question_id uuid;
    old_question_id uuid;
    weight_sum numeric;
BEGIN
    IF TG_OP <> 'DELETE' THEN
        new_question_id := NEW.exam_question_id;
    END IF;
    IF TG_OP <> 'INSERT' THEN
        old_question_id := OLD.exam_question_id;
    END IF;

    IF new_question_id IS NOT NULL
       AND EXISTS (SELECT 1 FROM exam_questions WHERE id = new_question_id) THEN
        SELECT COALESCE(SUM(weight), 0)
          INTO weight_sum
          FROM question_program_outcomes
         WHERE exam_question_id = new_question_id;

        IF weight_sum <> 1 THEN
            RAISE EXCEPTION
                'Program outcome weights for exam question % must total 1, got %',
                new_question_id, weight_sum;
        END IF;
    END IF;

    IF old_question_id IS NOT NULL
       AND old_question_id IS DISTINCT FROM new_question_id
       AND EXISTS (SELECT 1 FROM exam_questions WHERE id = old_question_id) THEN
        SELECT COALESCE(SUM(weight), 0)
          INTO weight_sum
          FROM question_program_outcomes
         WHERE exam_question_id = old_question_id;

        IF weight_sum <> 1 THEN
            RAISE EXCEPTION
                'Program outcome weights for exam question % must total 1, got %',
                old_question_id, weight_sum;
        END IF;
    END IF;

    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER question_po_weight_sum_check
AFTER INSERT OR UPDATE OR DELETE ON question_program_outcomes
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_question_po_weight_sum();

CREATE FUNCTION validate_paper_answer()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    paper_exam_id uuid;
    question_exam_id uuid;
    question_max_score numeric(8,3);
BEGIN
    SELECT exam_id INTO paper_exam_id
      FROM exam_papers
     WHERE id = NEW.exam_paper_id;

    SELECT exam_id, max_score
      INTO question_exam_id, question_max_score
      FROM exam_questions
     WHERE id = NEW.exam_question_id;

    IF paper_exam_id IS DISTINCT FROM question_exam_id THEN
        RAISE EXCEPTION 'Paper and question must belong to the same exam';
    END IF;

    IF NEW.predicted_score IS NOT NULL AND NEW.predicted_score > question_max_score THEN
        RAISE EXCEPTION 'Predicted score cannot exceed question maximum';
    END IF;

    IF NEW.final_score IS NOT NULL AND NEW.final_score > question_max_score THEN
        RAISE EXCEPTION 'Final score cannot exceed question maximum';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER paper_answers_validate
BEFORE INSERT OR UPDATE OF exam_paper_id, exam_question_id, predicted_score, final_score
ON paper_answers
FOR EACH ROW EXECUTE FUNCTION validate_paper_answer();

COMMIT;
