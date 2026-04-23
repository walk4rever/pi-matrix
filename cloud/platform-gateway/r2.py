from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path

import boto3
from botocore.config import Config

from config import settings

logger = logging.getLogger(__name__)
_client = None


def is_configured() -> bool:
    return bool(
        settings.r2_endpoint
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_bucket_name
        and settings.r2_public_url
    )


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
    return _client


def upload_file(file_name: str, content: bytes) -> str:
    if not is_configured():
        raise RuntimeError("R2 is not configured")

    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    ext = Path(file_name).suffix
    key = f"pi-matrix/{uuid.uuid4()}{ext}"
    _get_client().put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=content,
        ContentType=content_type,
        ContentDisposition=f'attachment; filename="{file_name}"',
        CacheControl="public, max-age=86400",
    )
    return f"{settings.r2_public_url.rstrip('/')}/{key}"
