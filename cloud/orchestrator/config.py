from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str

    executor_image: str = "pi-matrix/executor:latest"
    gateway_url: str = "http://gateway:4000/v1"
    gateway_key: str                # litellm master key
    platform_gateway_url: str = "http://platform-gateway:8000"
    hermes_model: str = "default"
    # Auxiliary vision routing for Hermes tools (vision_analyze, browser_vision, etc.)
    auxiliary_vision_provider: str = "main"
    auxiliary_vision_model: str = "vision"
    auxiliary_vision_base_url: str = "http://gateway:4000/v1"
    auxiliary_vision_api_key: str = ""
    # Optional platform-level web tool keys forwarded to executor containers.
    tavily_api_key: str = ""
    executor_port: int = 8080

    class Config:
        env_file = ".env"


settings = Settings()
