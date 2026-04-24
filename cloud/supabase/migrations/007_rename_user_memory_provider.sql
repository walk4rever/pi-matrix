-- Rename USER.md provider from memory_user_md to user_md.
-- Keep the migration idempotent and safe for existing rows.

INSERT INTO pi_matrix_user_credentials (
    user_id, provider, credential_key, credential_value, external_id, created_at, updated_at
)
SELECT
    user_id,
    'user_md',
    credential_key,
    credential_value,
    external_id,
    created_at,
    updated_at
FROM pi_matrix_user_credentials
WHERE provider = 'memory_user_md'
  AND credential_key = 'content'
ON CONFLICT (user_id, provider, credential_key)
DO UPDATE SET
    credential_value = EXCLUDED.credential_value,
    external_id = EXCLUDED.external_id,
    updated_at = EXCLUDED.updated_at;

DELETE FROM pi_matrix_user_credentials
WHERE provider = 'memory_user_md'
  AND credential_key = 'content';
