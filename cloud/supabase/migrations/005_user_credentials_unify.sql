-- Unified user credential store.
-- Replaces pi_matrix_feishu_drive_tokens and supports future providers.

CREATE TABLE IF NOT EXISTS pi_matrix_user_credentials (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider text NOT NULL,
    credential_key text NOT NULL,
    credential_value text NOT NULL,
    external_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(user_id, provider, credential_key)
);

ALTER TABLE pi_matrix_user_credentials ENABLE ROW LEVEL SECURITY;

-- Block all direct client access; service role bypasses RLS.
CREATE POLICY "service_only" ON pi_matrix_user_credentials
    USING (false);

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON pi_matrix_user_credentials TO service_role;

-- Indexes
CREATE INDEX IF NOT EXISTS pi_matrix_user_credentials_user_provider_idx
    ON pi_matrix_user_credentials (user_id, provider);
CREATE INDEX IF NOT EXISTS pi_matrix_user_credentials_provider_external_idx
    ON pi_matrix_user_credentials (provider, external_id);
CREATE INDEX IF NOT EXISTS pi_matrix_user_credentials_key_idx
    ON pi_matrix_user_credentials (provider, credential_key);

-- Migrate legacy Feishu Drive tokens into the unified table.
INSERT INTO pi_matrix_user_credentials (
    user_id, provider, credential_key, credential_value, external_id, created_at, updated_at
)
SELECT
    user_id, 'feishu_drive', 'access_token', access_token, open_id, created_at, updated_at
FROM pi_matrix_feishu_drive_tokens
ON CONFLICT (user_id, provider, credential_key)
DO UPDATE SET
    credential_value = EXCLUDED.credential_value,
    external_id = EXCLUDED.external_id,
    updated_at = EXCLUDED.updated_at;

INSERT INTO pi_matrix_user_credentials (
    user_id, provider, credential_key, credential_value, external_id, created_at, updated_at
)
SELECT
    user_id, 'feishu_drive', 'refresh_token', refresh_token, open_id, created_at, updated_at
FROM pi_matrix_feishu_drive_tokens
ON CONFLICT (user_id, provider, credential_key)
DO UPDATE SET
    credential_value = EXCLUDED.credential_value,
    external_id = EXCLUDED.external_id,
    updated_at = EXCLUDED.updated_at;

INSERT INTO pi_matrix_user_credentials (
    user_id, provider, credential_key, credential_value, external_id, created_at, updated_at
)
SELECT
    user_id, 'feishu_drive', 'expires_at', expires_at::text, open_id, created_at, updated_at
FROM pi_matrix_feishu_drive_tokens
ON CONFLICT (user_id, provider, credential_key)
DO UPDATE SET
    credential_value = EXCLUDED.credential_value,
    external_id = EXCLUDED.external_id,
    updated_at = EXCLUDED.updated_at;

DROP TABLE IF EXISTS pi_matrix_feishu_drive_tokens;
