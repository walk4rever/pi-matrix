"""
Docker container lifecycle management for user agent executors.
One stateless executor container per user, named pi-matrix-{user_id}.
"""
from __future__ import annotations

import re
import time

import docker
import httpx
from config import settings

_docker = docker.from_env()


def provision(user_id: str, image: str | None = None) -> str:
    """Start an executor container for a user. Returns the internal URL."""
    return _replace_container(user_id, image or settings.executor_image)


def upgrade(user_id: str, image: str | None = None, *, backup: bool = True) -> dict:
    """
    Replace a user's executor with a new image while keeping the user's /root volume.
    Rolls back to the previous image automatically if the new container fails health.
    """
    target_image = image or settings.executor_image
    previous_image = _current_image(user_id)

    if settings.docker_pull_on_upgrade:
        _docker.images.pull(target_image)

    backup_path = snapshot_home_volume(user_id) if backup else None

    try:
        endpoint = _replace_container(user_id, target_image)
        _wait_healthy(endpoint, timeout=settings.executor_upgrade_smoke_timeout)
    except Exception:
        if previous_image:
            _replace_container(user_id, previous_image)
        raise

    return {
        "user_id": user_id,
        "endpoint": endpoint,
        "image": target_image,
        "previous_image": previous_image,
        "backup_path": backup_path,
    }


def rollback(user_id: str, image: str) -> dict:
    """Replace a user's executor with a known previous image."""
    endpoint = _replace_container(user_id, image)
    _wait_healthy(endpoint, timeout=settings.executor_upgrade_smoke_timeout)
    return {"user_id": user_id, "endpoint": endpoint, "image": image}


def snapshot_home_volume(user_id: str) -> str:
    """Create a tar.gz snapshot of the user's home volume on the Docker host."""
    volume = _home_volume_name(user_id)
    safe_user_id = re.sub(r"[^A-Za-z0-9_.-]", "_", user_id)
    ts = time.strftime("%Y%m%d-%H%M%S")
    filename = f"pi-matrix-home-{safe_user_id}-{ts}.tgz"

    _docker.volumes.get(volume)
    _docker.images.pull("alpine:3.20")
    _docker.containers.run(
        "alpine:3.20",
        ["sh", "-lc", f"mkdir -p /backup && tar -C /from -czf /backup/{filename} ."],
        remove=True,
        volumes={
            volume: {"bind": "/from", "mode": "ro"},
            settings.executor_upgrade_backup_dir: {"bind": "/backup", "mode": "rw"},
        },
    )
    return f"{settings.executor_upgrade_backup_dir.rstrip('/')}/{filename}"


def _replace_container(user_id: str, image: str) -> str:
    name = _container_name(user_id)
    _remove_if_exists(name)
    _run_container(user_id, image)
    return f"http://{name}:{settings.executor_port}"


def _run_container(user_id: str, image: str) -> None:
    name = _container_name(user_id)
    _docker.containers.run(
        image,
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
            "TAVILY_API_KEY": settings.tavily_api_key,
            "HERMES_VERSION": settings.hermes_version,
        },
        volumes={
            _home_volume_name(user_id): {"bind": "/root", "mode": "rw"},
        },
        network="pi-matrix",
        labels={
            "pi-matrix.user_id": user_id,
            "pi-matrix.executor_image": image,
            "pi-matrix.hermes_version": settings.hermes_version,
        },
    )


def deprovision(user_id: str) -> None:
    """Stop and remove a user's executor container and persisted volumes."""
    _remove_if_exists(_container_name(user_id))
    _remove_volume_if_exists(_home_volume_name(user_id))
    # Legacy volume cleanup
    _remove_volume_if_exists(f"pi-matrix-hermes-{user_id}")
    _remove_volume_if_exists(f"pi-matrix-state-{user_id}")
    _remove_volume_if_exists(f"pi-matrix-skills-{user_id}")
    _remove_volume_if_exists(f"pi-matrix-workspace-{user_id}")


def _home_volume_name(user_id: str) -> str:
    return f"pi-matrix-home-{user_id}"


def _container_name(user_id: str) -> str:
    return f"pi-matrix-{user_id}"


def _current_image(user_id: str) -> str | None:
    try:
        c = _docker.containers.get(_container_name(user_id))
        return c.attrs.get("Config", {}).get("Image")
    except docker.errors.NotFound:
        return None


def _wait_healthy(endpoint: str, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not checked"
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{endpoint}/health", timeout=3.0)
            if resp.status_code == 200 and resp.json().get("ok") is True:
                return
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise RuntimeError(f"executor health check failed for {endpoint}: {last_error}")


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
