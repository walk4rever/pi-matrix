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
    state_volume = _state_volume_name(user_id)

    # Remove existing container if present (re-provision case)
    _remove_if_exists(name)

    # Keep Hermes session DB on a per-user named volume so conversation
    # history survives container recreation.
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
            "HERMES_STATE_DB_PATH": "/root/.hermes/state/state.db",
            "HERMES_SESSION_SOURCE": "feishu",
        },
        volumes={
            state_volume: {"bind": "/root/.hermes/state", "mode": "rw"},
        },
        network="pi-matrix",  # join the same docker network
        labels={"pi-matrix.user_id": user_id},
    )

    return f"http://{name}:{settings.container_port}"


def deprovision(user_id: str) -> None:
    """Stop and remove a user's hermes container and persisted session volume."""
    _remove_if_exists(f"pi-matrix-{user_id}")
    _remove_volume_if_exists(_state_volume_name(user_id))


def _state_volume_name(user_id: str) -> str:
    return f"pi-matrix-state-{user_id}"


def _remove_if_exists(name: str) -> None:
    try:
        c = _docker.containers.get(name)
        c.stop(timeout=5)
        c.remove()
    except docker.errors.NotFound:
        pass


def _remove_volume_if_exists(name: str) -> None:
    try:
        v = _docker.volumes.get(name)
        v.remove(force=True)
    except docker.errors.NotFound:
        pass
