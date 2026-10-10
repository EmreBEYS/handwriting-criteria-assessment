BEGIN;

CREATE TABLE refresh_sessions (
    jti uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    replaced_by_jti uuid,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_refresh_sessions_user_id ON refresh_sessions(user_id);
CREATE INDEX ix_refresh_sessions_expires_at ON refresh_sessions(expires_at);

COMMIT;
