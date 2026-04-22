CREATE TABLE IF NOT EXISTS pi_matrix_feishu_drive_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    open_id text NOT NULL,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(user_id),
    UNIQUE(open_id)
);

ALTER TABLE pi_matrix_feishu_drive_tokens ENABLE ROW LEVEL SECURITY;

-- Block all direct client access; service role bypasses RLS.
CREATE POLICY "service_only" ON pi_matrix_feishu_drive_tokens
    USING (false);

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON pi_matrix_feishu_drive_tokens TO service_role;

-- Index
CREATE INDEX ON pi_matrix_feishu_drive_tokens (open_id);
CREATE INDEX ON pi_matrix_feishu_drive_tokens (user_id);
