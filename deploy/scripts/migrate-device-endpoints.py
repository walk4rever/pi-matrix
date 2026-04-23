#!/usr/bin/env python3
"""
Normalize legacy cloud device endpoints in Supabase:
- .../inbox   -> base URL
- .../execute -> base URL

Required env vars:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY

Usage:
  python3 deploy/scripts/migrate-device-endpoints.py [--dry-run]
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any


def _normalize(endpoint: str) -> str:
    value = (endpoint or "").strip().rstrip("/")
    if value.endswith("/inbox"):
        return value[:-6]
    if value.endswith("/execute"):
        return value[:-8]
    return value


def _http_json(method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def main() -> int:
    dry_run = "--dry-run" in sys.argv[1:]

    base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not base_url or not service_key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY", file=sys.stderr)
        return 2

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    select = urllib.parse.quote("id,user_id,endpoint,instance_type", safe=",")
    query_url = (
        f"{base_url}/rest/v1/pi_matrix_devices"
        f"?select={select}&instance_type=eq.cloud"
    )
    rows = _http_json("GET", query_url, headers) or []
    if not isinstance(rows, list):
        print("Unexpected response format", file=sys.stderr)
        return 1

    changed = 0
    for row in rows:
        row_id = row.get("id")
        endpoint = row.get("endpoint") or ""
        normalized = _normalize(endpoint)
        if not row_id or normalized == endpoint:
            continue

        changed += 1
        user_id = row.get("user_id", "")
        print(f"[plan] user_id={user_id} id={row_id}: {endpoint} -> {normalized}")
        if dry_run:
            continue

        patch_headers = {**headers, "Prefer": "return=minimal"}
        patch_url = f"{base_url}/rest/v1/pi_matrix_devices?id=eq.{urllib.parse.quote(str(row_id), safe='')}"
        _http_json("PATCH", patch_url, patch_headers, {"endpoint": normalized})

    if dry_run:
        print(f"Dry-run complete. Rows to update: {changed}")
    else:
        print(f"Migration complete. Rows updated: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
