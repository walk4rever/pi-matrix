"""
pi-matrix Agent Executor — stateless turn runner.

Receives a turn payload (history + message), runs Hermes AIAgent,
and returns the response. No session persistence, no platform logic,
no credentials.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

# Hermes — installed via git in Dockerfile
from run_agent import AIAgent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="pi-matrix executor", version="0.2.0")

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
GATEWAY_URL = os.environ["GATEWAY_URL"]      # LiteLLM Proxy
GATEWAY_KEY = os.environ["GATEWAY_KEY"]      # LiteLLM master key
HERMES_MODEL = os.environ.get("HERMES_MODEL", "default")
PROGRESS_NOTIFY_URL = os.environ.get("PROGRESS_NOTIFY_URL", "http://platform-gateway:8000/internal/notify")
PROGRESS_NOTIFY_SECRET = os.environ.get("PROGRESS_NOTIFY_SECRET", GATEWAY_KEY)

HERMES_ENABLED_TOOLSETS = [
    "file",
    "terminal",
    "skills",
    "memory",
    "clarify",
    "code_execution",
    "delegation",
    "todo",
    "tts",
    "vision",
    "browser",
    "feishu_doc",
    "feishu_drive",
]

_WORKSPACE = Path(os.environ.get("HERMES_WORKSPACE_DIR", "/root/.hermes/workspace"))
_UPLOADS_DIR = _WORKSPACE / "uploads"
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
class Attachment(BaseModel):
    name: str | None = None
    message_type: str | None = None
    content_b64: str


class ExecuteRequest(BaseModel):
    message: str
    history: list[dict[str, Any]]
    context_prompt: str | None = None
    session_id: str
    user_id: str
    attachments: list[Attachment] | None = None
    user_tokens: dict[str, str] | None = None


class ExecuteResponse(BaseModel):
    response: str
    files: list[dict[str, str]] | None = None
    metadata: dict[str, Any] | None = None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _sanitize(name: str) -> str:
    name = (name or "file.bin").strip()
    name = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return safe[:120] or "file.bin"


def _materialize(attachments: list[Attachment] | None) -> tuple[list[Path], str]:
    saved: list[Path] = []
    notes: list[str] = []
    if not attachments:
        return saved, ""

    for idx, att in enumerate(attachments, start=1):
        if not att.content_b64:
            continue
        try:
            raw = base64.b64decode(att.content_b64)
        except Exception:
            notes.append(f"- Attachment #{idx} decode failed")
            continue
        dest = _UPLOADS_DIR / f"{idx}_{_sanitize(att.name)}"
        dest.write_bytes(raw)
        saved.append(dest)
        notes.append(f"- {dest}")

    note = "User uploaded attachments:\n" + "\n".join(notes) if notes else ""
    return saved, note


_FILE_RE = re.compile(r"(/[^\s'\"`]+)")
_MAX_FILE_RETURN = 50 * 1024 * 1024


def _collect_files(text: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in _FILE_RE.findall(text or ""):
        if m in seen:
            continue
        seen.add(m)
        p = Path(m)
        try:
            if not p.is_file():
                continue
        except Exception:
            continue
        data = p.read_bytes()
        if len(data) > _MAX_FILE_RETURN:
            logger.warning("skip oversized %s (%d bytes)", p.name, len(data))
            continue
        files.append({
            "name": p.name,
            "content_b64": base64.b64encode(data).decode("ascii"),
        })
    return files


def _inject_user_tokens(tokens: dict[str, str] | None) -> None:
    """
    Inject user tokens into process env for Hermes Feishu tools.
    One executor container serves one user, so this per-turn overwrite is safe.
    """
    data = tokens or {}
    access = (data.get("feishu_access_token") or "").strip()
    refresh = (data.get("feishu_refresh_token") or "").strip()
    expires = (data.get("feishu_expires_at") or "").strip()

    mapping = {
        "FEISHU_ACCESS_TOKEN": access,
        "FEISHU_USER_ACCESS_TOKEN": access,
        "LARK_ACCESS_TOKEN": access,
        "FEISHU_REFRESH_TOKEN": refresh,
        "FEISHU_USER_REFRESH_TOKEN": refresh,
        "LARK_REFRESH_TOKEN": refresh,
        "FEISHU_TOKEN_EXPIRES_AT": expires,
    }
    for key, value in mapping.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


class ProgressEmitter:
    def __init__(self, open_id: str):
        self._open_id = open_id
        self._client = httpx.Client(timeout=4.0)
        self._last_text = ""
        self._last_status_ts = 0.0
        self._tool_call_name: dict[str, str] = {}

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def _send(self, text: str, throttle_seconds: float = 0.0) -> None:
        text = (text or "").strip()
        if not text or not PROGRESS_NOTIFY_URL:
            return
        now = time.time()
        if throttle_seconds > 0 and (now - self._last_status_ts) < throttle_seconds:
            return
        if text == self._last_text:
            return

        self._last_text = text
        self._last_status_ts = now
        try:
            self._client.post(
                PROGRESS_NOTIFY_URL,
                data={"open_id": self._open_id, "text": text},
                headers={"x-internal-secret": PROGRESS_NOTIFY_SECRET},
            )
        except Exception:
            logger.debug("send progress failed", exc_info=True)

    def _resolve_tool_name(self, raw: str) -> str:
        if raw in self._tool_call_name:
            return self._tool_call_name[raw]
        if raw.startswith("call_"):
            return "工具调用"
        return raw

    def _extract_tool_name(self, *args, **kwargs) -> str:
        for key in ("tool_name", "name", "tool"):
            if key in kwargs and kwargs[key]:
                return self._resolve_tool_name(str(kwargs[key]))
        if len(args) >= 2 and isinstance(args[1], str) and args[1].strip():
            return args[1]

        obj = kwargs.get("tool_call") or kwargs.get("call")
        if isinstance(obj, dict):
            fn = obj.get("function")
            if isinstance(fn, dict) and fn.get("name"):
                return str(fn["name"])
            if obj.get("name"):
                return str(obj["name"])
            if obj.get("id"):
                return self._resolve_tool_name(str(obj["id"]))

        if args:
            first = args[0]
            if isinstance(first, str):
                return self._resolve_tool_name(first)
            if isinstance(first, dict):
                for key in ("tool_name", "name", "tool"):
                    if first.get(key):
                        return self._resolve_tool_name(str(first[key]))
                fn = first.get("function")
                if isinstance(fn, dict) and fn.get("name"):
                    return str(fn["name"])
                if first.get("id"):
                    return self._resolve_tool_name(str(first["id"]))
        return "工具调用"

    @staticmethod
    def _extract_status_text(*args, **kwargs) -> str:
        for key in ("status", "message", "text"):
            if key in kwargs and kwargs[key]:
                return str(kwargs[key])
        if args:
            first = args[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("status", "message", "text"):
                    if first.get(key):
                        return str(first[key])
        return "处理中..."

    def _short(self, value: str, limit: int = 90) -> str:
        value = (value or "").strip().replace("\n", " ")
        return value if len(value) <= limit else value[:limit] + "…"

    def _extract_tool_detail(self, *args, **kwargs) -> str:
        raw = None
        if len(args) >= 3 and args[2]:
            raw = args[2]
        elif kwargs.get("args"):
            raw = kwargs.get("args")
        if raw is None:
            return ""

        if isinstance(raw, dict):
            data = raw
        else:
            text = str(raw).strip()
            if not text:
                return ""
            try:
                data = json.loads(text)
            except Exception:
                return self._short(text)

        for key in ("command", "query", "question", "prompt", "code", "path", "pattern"):
            if key in data and data[key]:
                return self._short(str(data[key]))
        return ""

    def tool_start(self, *args, **kwargs) -> None:
        tool = self._extract_tool_name(*args, **kwargs)
        detail = self._extract_tool_detail(*args, **kwargs)
        if detail:
            self._send(f"🔧 正在执行：{tool}（{detail}）")
        else:
            self._send(f"🔧 正在执行：{tool}")

    def tool_complete(self, *args, **kwargs) -> None:
        return

    def status(self, *args, **kwargs) -> None:
        status = self._extract_status_text(*args, **kwargs)
        if status.strip().lower() in {"lifecycle", "running"}:
            return
        self._send(f"… {status}", throttle_seconds=2.0)

    def tool_gen(self, *args, **kwargs) -> None:
        candidates = []
        candidates.extend(args)
        candidates.extend(v for v in kwargs.values())
        for item in candidates:
            if not isinstance(item, list):
                continue
            for call in item:
                if not isinstance(call, dict):
                    continue
                call_id = call.get("id")
                fn = call.get("function")
                if call_id and isinstance(fn, dict) and fn.get("name"):
                    self._tool_call_name[str(call_id)] = str(fn["name"])


# ------------------------------------------------------------------
# Turn execution
# ------------------------------------------------------------------
def _run_turn(req: ExecuteRequest) -> ExecuteResponse:
    paths, note = _materialize(req.attachments)
    emitter = ProgressEmitter(req.user_id)

    try:
        _inject_user_tokens(req.user_tokens)
        parts: list[str] = []
        if req.context_prompt:
            parts.append(req.context_prompt)
        if note:
            parts.append(note)
        if paths:
            parts.append("Available local files:\n" + "\n".join(f"- {p}" for p in paths))
        parts.append(req.message)
        turn_text = "\n\n".join(parts).strip()

        # Stateless agent — no session_db, no persistence.
        agent = AIAgent(
            model=HERMES_MODEL,
            base_url=GATEWAY_URL,
            api_key=GATEWAY_KEY,
            session_id=req.session_id,
            platform="feishu",
            user_id=req.user_id,
            enabled_toolsets=HERMES_ENABLED_TOOLSETS,
            tool_start_callback=emitter.tool_start,
            tool_complete_callback=emitter.tool_complete,
            tool_gen_callback=emitter.tool_gen,
            status_callback=emitter.status,
        )

        result = agent.run_conversation(turn_text, conversation_history=req.history)
        response = result["final_response"] if isinstance(result, dict) else str(result)

        files = _collect_files(response)

        return ExecuteResponse(
            response=response,
            files=files or None,
            metadata={
                "api_calls": result.get("api_calls", 0) if isinstance(result, dict) else 0,
            },
        )
    finally:
        emitter.close()


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    loop = __import__("asyncio").get_event_loop()
    return await loop.run_in_executor(None, _run_turn, req)


@app.get("/health")
def health():
    return {"ok": True}
