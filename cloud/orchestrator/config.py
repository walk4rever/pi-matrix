from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str

    docker_image: str = "pi-matrix/hermes-agent:latest"
    router_reply_url: str = "http://router:8000/reply"
    gateway_url: str = "http://gateway:4000/v1"
    gateway_key: str                # litellm master key
    hermes_model: str = "default"
    # Auxiliary vision routing for Hermes tools (vision_analyze, browser_vision, etc.)
    # Defaults route through our internal LiteLLM gateway vision alias.
    auxiliary_vision_provider: str = "main"
    auxiliary_vision_model: str = "vision"
    auxiliary_vision_base_url: str = "http://gateway:4000/v1"
    auxiliary_vision_api_key: str = ""
    container_port: int = 8080

    class Config:
        env_file = ".env"


settings = Settings()
