"""
Docker container lifecycle management for user hermes instances.
One container per user, named pi-matrix-{user_id}.
"""
import docker
from config import settings

_docker = docker.from_env()


def provision(user_id: str) -> str:
    """Start a hermes container for a user. Returns the container's internal URL."""
    name = f"pi-matrix-{user_id}"

    # Remove existing container if present (re-provision case)
    _remove_if_exists(name)

    container = _docker.containers.run(
        settings.docker_image,
        name=name,
        detach=True,
        restart_policy={"Name": "always"},
        environment={
            "ROUTER_REPLY_URL": settings.router_reply_url,
            "HERMES_MODEL": settings.hermes_model,
            "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        },
        labels={"pi-matrix.user_id": user_id},
    )

    # Get assigned IP on the default bridge network
    container.reload()
    ip = container.attrs["NetworkSettings"]["IPAddress"]
    return f"http://{ip}:{settings.container_port}"


def deprovision(user_id: str) -> None:
    """Stop and remove a user's hermes container."""
    _remove_if_exists(f"pi-matrix-{user_id}")


def _remove_if_exists(name: str) -> None:
    try:
        c = _docker.containers.get(name)
        c.stop(timeout=5)
        c.remove()
    except docker.errors.NotFound:
        pass
