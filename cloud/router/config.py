from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""

    # Secret used by platform Hermes Gateway wrapper when posting normalized
    # inbound events to router /ingress/hermes-event.
    hermes_ingress_secret: str = ""
    # Router ingress endpoint consumed by the wrapper service.
    hermes_router_ingress_url: str = "http://router:8000/ingress/hermes-event"

    supabase_url: str
    supabase_service_key: str
    dashboard_url: str = "https://matrix.air7.fun"
    api_base_url: str = "https://api.matrix.air7.fun"

    class Config:
        env_file = ".env"


settings = Settings()
