from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str

    docker_image: str = "pi-matrix/hermes-agent:latest"
    router_reply_url: str           # e.g. https://router.pi-matrix.com/reply
    hermes_model: str = "anthropic/claude-haiku-4-5"
    anthropic_api_key: str = ""     # passed into each container
    container_port: int = 8080

    class Config:
        env_file = ".env"


settings = Settings()
