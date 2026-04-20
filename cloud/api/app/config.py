from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    gateway_url: str = ""
    gateway_key: str = ""
    orchestrator_url: str = "http://orchestrator:8000"
    resend_api_key: str = ""
    from_email: str = "pi-matrix <hi@air7.fun>"
    dashboard_url: str = "https://matrix.air7.fun"

    class Config:
        env_file = ".env"


settings = Settings()
