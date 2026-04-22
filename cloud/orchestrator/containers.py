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
            "HERMES_STATE_DB_PATH": "/root/.hermes/state/state.db",
            "HERMES_WORKSPACE_DIR": "/root/.hermes/workspace",
            "TERMINAL_CWD": "/root",
            "MESSAGING_CWD": "/root",
            "HERMES_SESSION_SOURCE": "feishu",
            # Hermes auxiliary vision config (used by vision_analyze/browser_vision).
            # Route through internal LiteLLM gateway alias "vision" by default.
            "AUXILIARY_VISION_PROVIDER": settings.auxiliary_vision_provider,
            "AUXILIARY_VISION_MODEL": settings.auxiliary_vision_model,
            "AUXILIARY_VISION_BASE_URL": settings.auxiliary_vision_base_url,
            "AUXILIARY_VISION_API_KEY": settings.auxiliary_vision_api_key or settings.gateway_key,
        },
        volumes={
            _home_volume_name(user_id): {"bind": "/root", "mode": "rw"},
        },
        network="pi-matrix",  # join the same docker network
        labels={"pi-matrix.user_id": user_id},
    )

    return f"http://{name}:{settings.container_port}"


def deprovision(user_id: str) -> None:
    """Stop and remove a user's hermes container and persisted user volumes."""
    _remove_if_exists(f"pi-matrix-{user_id}")
    _remove_volume_if_exists(_home_volume_name(user_id))
    # Legacy volume cleanup (safe no-op if they don't exist)
    _remove_volume_if_exists(f"pi-matrix-hermes-{user_id}")
    _remove_volume_if_exists(f"pi-matrix-state-{user_id}")
    _remove_volume_if_exists(f"pi-matrix-skills-{user_id}")
    _remove_volume_if_exists(f"pi-matrix-workspace-{user_id}")


def _home_volume_name(user_id: str) -> str:
    return f"pi-matrix-home-{user_id}"


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
