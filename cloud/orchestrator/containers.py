"""
Docker container lifecycle management for user agent executors.
One stateless executor container per user, named pi-matrix-{user_id}.
"""
import docker
from config import settings

_docker = docker.from_env()


def provision(user_id: str) -> str:
    """Start an executor container for a user. Returns the internal URL."""
    name = f"pi-matrix-{user_id}"
    _remove_if_exists(name)

    _docker.containers.run(
        settings.executor_image,
        name=name,
        detach=True,
        restart_policy={"Name": "always"},
        environment={
            "GATEWAY_URL": settings.gateway_url,
            "GATEWAY_KEY": settings.gateway_key,
            "PROGRESS_NOTIFY_URL": f"{settings.platform_gateway_url}/internal/notify",
            "PROGRESS_NOTIFY_SECRET": settings.gateway_key,
            "HERMES_MODEL": settings.hermes_model,
            # Enable cronjob tool availability in executor runtime.
            "HERMES_EXEC_ASK": "1",
            # Mark non-local messaging context so send_message tool is available.
            "HERMES_SESSION_PLATFORM": "feishu",
            "HERMES_WORKSPACE_DIR": "/root/.hermes/workspace",
            "TERMINAL_CWD": "/root",
            "MESSAGING_CWD": "/root",
            "AUXILIARY_VISION_PROVIDER": settings.auxiliary_vision_provider,
            "AUXILIARY_VISION_MODEL": settings.auxiliary_vision_model,
            "AUXILIARY_VISION_BASE_URL": settings.auxiliary_vision_base_url,
            "AUXILIARY_VISION_API_KEY": settings.auxiliary_vision_api_key or settings.gateway_key,
        },
        volumes={
            _home_volume_name(user_id): {"bind": "/root", "mode": "rw"},
        },
        network="pi-matrix",
        labels={"pi-matrix.user_id": user_id},
    )

    return f"http://{name}:{settings.executor_port}"


def deprovision(user_id: str) -> None:
    """Stop and remove a user's executor container and persisted volumes."""
    _remove_if_exists(f"pi-matrix-{user_id}")
    _remove_volume_if_exists(_home_volume_name(user_id))
    # Legacy volume cleanup
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
