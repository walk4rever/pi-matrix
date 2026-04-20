from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    gateway_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
