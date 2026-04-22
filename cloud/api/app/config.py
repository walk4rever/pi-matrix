from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    gateway_url: str = ""
    gateway_key: str = ""
    orchestrator_url: str = "http://orchestrator:8000"
    router_reply_url: str = "http://router:8000/reply"
    resend_api_key: str = ""
    from_email: str = "pi-matrix <matrix@air7.fun>"
    dashboard_url: str = "https://matrix.air7.fun"
    api_base_url: str = "https://api.matrix.air7.fun"
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
