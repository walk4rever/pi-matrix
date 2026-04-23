"""
Light-weight session store aligned with Hermes SessionStore interface.
Uses JSONL for transcripts and JSON for metadata.
Can be swapped for gateway.session.SessionStore when Hermes exports it cleanly.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class SessionEntry:
    session_key: str
    session_id: str
    user_id: str
    platform: str
    created_at: str
    updated_at: str
    last_prompt_tokens: int = 0


class SimpleSessionStore:
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    def _meta_path(self, session_key: str) -> Path:
        return self.sessions_dir / f"{self._safe_name(session_key)}.json"

    def _tx_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{self._safe_name(session_id)}.jsonl"

    def get_or_create_session(self, source) -> SessionEntry:
        """source must have .platform (with .value), .user_id, .chat_id attributes."""
        platform_str = source.platform.value if hasattr(source.platform, "value") else str(source.platform)
        session_key = f"{platform_str}:{source.user_id}"
        path = self._meta_path(session_key)

        if path.exists():
            data = json.loads(path.read_text())
            data["updated_at"] = datetime.now().isoformat()
            path.write_text(json.dumps(data, indent=2))
            return SessionEntry(**data)

        session_id = f"pm-{datetime.now().strftime('%Y%m%d%H%M%S')}-{source.user_id[:16]}"
        entry = SessionEntry(
            session_key=session_key,
            session_id=session_id,
            user_id=source.user_id,
            platform=platform_str,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        path.write_text(json.dumps(asdict(entry), indent=2))
        return entry

    def load_transcript(self, session_id: str) -> list[dict[str, Any]]:
        path = self._tx_path(session_id)
        if not path.exists():
            return []
        msgs: list[dict[str, Any]] = []
        for line in path.read_text().strip().splitlines():
            if line:
                msgs.append(json.loads(line))
        return msgs

    def append_to_transcript(self, session_id: str, entry: dict[str, Any]) -> None:
        path = self._tx_path(session_id)
        with path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def update_session(self, session_key: str, **kwargs: Any) -> None:
        path = self._meta_path(session_key)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        data.update(kwargs)
        path.write_text(json.dumps(data, indent=2))

    def estimate_tokens(self, session_id: str) -> int:
        """Rough token count for hygiene decisions."""
        msgs = self.load_transcript(session_id)
        total_chars = sum(len(m.get("content", "")) for m in msgs)
        # ~4 chars per token for CJK/English mixed text
        return total_chars // 4

    def replace_transcript(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        path = self._tx_path(session_id)
        path.write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\n")

    def reset_session(self, session_key: str) -> None:
        path = self._meta_path(session_key)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        old_sid = data.get("session_id")
        if old_sid:
            old_tx = self._tx_path(old_sid)
            if old_tx.exists():
                old_tx.rename(old_tx.with_suffix(".jsonl.bak"))
        data["session_id"] = f"pm-{datetime.now().strftime('%Y%m%d%H%M%S')}-{data['user_id'][:16]}"
        data["updated_at"] = datetime.now().isoformat()
        path.write_text(json.dumps(data, indent=2))
