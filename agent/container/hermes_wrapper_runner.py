"""Platform wrapper service powered by Hermes native Feishu adapter.

This process is the single shared-bot inbound consumer. It uses Hermes'
FeishuAdapter to normalize inbound events and attachment handling, then forwards
those normalized events to router /ingress/hermes-event for user routing.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import contextlib
import os
from typing import Any

import httpx
from fastapi import FastAPI

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.feishu import FeishuAdapter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="pi-matrix hermes-native wrapper", version="0.1.0")

ROUTER_INGRESS_URL = os.environ.get("HERMES_ROUTER_INGRESS_URL", "http://router:8000/ingress/hermes-event")
INGRESS_SECRET = os.environ.get("HERMES_INGRESS_SECRET", "")

_adapter: FeishuAdapter | None = None
_adapter_task: asyncio.Task | None = None


def _read_attachment(path: str, media_type: str) -> dict[str, Any] | None:
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        logger.warning("failed to read attachment path=%s", path, exc_info=True)
        return None

    return {
        "name": os.path.basename(path),
        "message_type": media_type or "file",
        "content_b64": base64.b64encode(raw).decode("ascii"),
    }


async def _post_event(event: MessageEvent) -> None:
    open_id = event.source.user_id if event.source else None
    if not open_id:
        logger.warning("drop event without source.user_id message_id=%s", event.message_id)
        return

    logger.info(
        "forward event message_id=%s open_id=%s type=%s media=%d",
        event.message_id,
        open_id,
        event.message_type.value if event.message_type else "unknown",
        len(event.media_urls or []),
    )

    attachments: list[dict[str, Any]] = []
    media_urls = event.media_urls or []
    media_types = event.media_types or []
    for idx, path in enumerate(media_urls):
        mtype = media_types[idx] if idx < len(media_types) else ""
        att = _read_attachment(path, mtype)
        if att:
            attachments.append(att)

    payload = {
        "open_id": open_id,
        "text": event.text or "",
        "message_type": event.message_type.value if event.message_type else None,
        "raw_content": None,
        "attachments": attachments or None,
        "message_id": event.message_id,
        "reaction_id": None,
    }

    headers = {}
    if INGRESS_SECRET:
        headers["x-ingress-secret"] = INGRESS_SECRET

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(ROUTER_INGRESS_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("router ingress failed status=%s body=%s", resp.status_code, resp.text[:300])


async def _message_handler(event: MessageEvent) -> str | None:
    await _post_event(event)
    return None


async def _run_adapter() -> None:
    global _adapter

    platform_cfg = PlatformConfig(enabled=True, extra={})
    adapter = FeishuAdapter(platform_cfg)
    adapter.set_message_handler(_message_handler)
    _adapter = adapter

    connected = await adapter.connect()
    if not connected:
        logger.error("FeishuAdapter failed to connect")
        return

    logger.info("FeishuAdapter connected")
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        raise
    finally:
        await adapter.disconnect()


@app.on_event("startup")
async def startup() -> None:
    global _adapter_task
    _adapter_task = asyncio.create_task(_run_adapter())


@app.on_event("shutdown")
async def shutdown() -> None:
    global _adapter_task
    if _adapter_task:
        _adapter_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _adapter_task


@app.get("/health")
def health() -> dict[str, bool]:
    running = bool(_adapter and _adapter.is_connected)
    return {"ok": running}
