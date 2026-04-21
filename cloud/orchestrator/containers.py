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

    _docker.containers.run(
        settings.docker_image,
        name=name,
        detach=True,
        restart_policy={"Name": "always"},
        environment={
            "ROUTER_REPLY_URL": settings.router_reply_url,
            "GATEWAY_URL": settings.gateway_url,
            "GATEWAY_KEY": settings.gateway_key,
            "HERMES_MODEL": settings.hermes_model,
        },
        network="pi-matrix",  # join the same docker network
        labels={"pi-matrix.user_id": user_id},
    )

    return f"http://{name}:{settings.container_port}"


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
