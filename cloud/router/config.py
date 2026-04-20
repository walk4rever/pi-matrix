from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_encrypt_key: str = ""

    supabase_url: str
    supabase_service_key: str
    dashboard_url: str = "https://pi-matrix.vercel.app"

    class Config:
        env_file = ".env"


settings = Settings()
