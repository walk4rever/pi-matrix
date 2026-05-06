from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str

    hermes_version: str = "v2026.4.30"
    executor_image: str = "pi-matrix/executor:hermes-v2026.4.30"
    gateway_url: str = "http://gateway:4000/v1"
    gateway_key: str                # litellm master key
    platform_gateway_url: str = "http://message:8000"
    hermes_model: str = "default"
    # Auxiliary vision routing for Hermes tools (vision_analyze, browser_vision, etc.)
    auxiliary_vision_provider: str = "main"
    auxiliary_vision_model: str = "vision"
    auxiliary_vision_base_url: str = "http://gateway:4000/v1"
    auxiliary_vision_api_key: str = ""
    # Optional platform-level web tool keys forwarded to executor containers.
    tavily_api_key: str = ""
    executor_port: int = 8080
    docker_pull_on_upgrade: bool = True
    executor_upgrade_backup_dir: str = "/var/backups/pi-matrix/hermes"
    executor_upgrade_smoke_timeout: float = 45.0

    class Config:
        env_file = ".env"


settings = Settings()
