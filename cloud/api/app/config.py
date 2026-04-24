from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    gateway_url: str = ""
    gateway_key: str = ""
    orchestrator_url: str = "http://orchestrator:8000"
    platform_gateway_url: str = "http://message:8000"
    resend_api_key: str = ""
    from_email: str = "pi-matrix <matrix@air7.fun>"
    dashboard_url: str = "https://matrix.air7.fun"
    api_base_url: str = "https://relay.air7.fun/pm/api"
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
