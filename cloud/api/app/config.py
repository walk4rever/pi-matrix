from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    gateway_url: str = ""
    gateway_key: str = ""
    orchestrator_url: str = "http://orchestrator:8000"

    class Config:
        env_file = ".env"


settings = Settings()
