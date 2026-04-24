from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Feishu credentials — ONLY held here, never shipped to executors
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""

    # Supabase for user/device resolution
    supabase_url: str
    supabase_service_key: str

    # LiteLLM Gateway (internal)
    gateway_url: str = "http://gateway:4000/v1"
    gateway_key: str = ""

    # Session persistence
    sessions_dir: str = "/app/sessions"
    dashboard_url: str = "https://matrix.air7.fun"
    api_base_url: str = "https://relay.air7.fun/pm/api"

    # Cloudflare R2 fallback for large-file delivery
    r2_endpoint: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "pi-matrix"
    r2_public_url: str = ""

    # Executor HTTP call
    executor_timeout: float = 180.0

    # Session hygiene
    session_token_limit: int = 6000   # trigger compression above this
    session_keep_recent: int = 6      # messages to preserve during compression

    # Optional allowlist (comma-separated open_ids). Empty = allow all bound users.
    allowed_users: str = ""

    @property
    def allowed_users_set(self) -> set[str]:
        return {u.strip() for u in self.allowed_users.split(",") if u.strip()}

    class Config:
        env_file = ".env"


settings = Settings()
