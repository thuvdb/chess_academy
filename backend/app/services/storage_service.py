"""
Storage Service for CAMS.
Supports:
  - MinIO / S3-compatible Object Storage (when configured and reachable)
  - Local filesystem storage fallback (served via FastAPI /scans mount)
"""

import io
import os
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Local storage fallback directory
DEFAULT_STORAGE = Path(__file__).resolve().parent.parent.parent / "storage" / "scans"
SCAN_STORAGE_PATH = Path(os.getenv("SCAN_STORAGE_PATH", str(DEFAULT_STORAGE)))
SCAN_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Base URL for local files
STORAGE_BASE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8000/scans")

# MinIO client singleton
_minio_client = None
_minio_initialized = False
_minio_available = False


def _get_minio_client():
    """Initialize and verify MinIO client connection lazily."""
    global _minio_client, _minio_initialized, _minio_available
    if _minio_initialized:
        return _minio_client if _minio_available else None

    _minio_initialized = True
    try:
        from minio import Minio

        endpoint = getattr(settings, "MINIO_ENDPOINT", "localhost:9000")
        access_key = getattr(settings, "MINIO_ACCESS_KEY", "cams_admin")
        secret_key = getattr(settings, "MINIO_SECRET_KEY", "cams_admin123")
        secure = getattr(settings, "MINIO_SECURE", False)

        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        bucket = getattr(settings, "MINIO_BUCKET", "chess-academy")
        # Check connection / bucket existence
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("MinIO bucket '%s' created successfully", bucket)
        else:
            logger.info("MinIO bucket '%s' verified", bucket)

        _minio_client = client
        _minio_available = True
        logger.info("MinIO storage initialized at %s", endpoint)
        return _minio_client
    except Exception as exc:
        logger.warning(
            "MinIO not reachable at %s (%s). Using local storage fallback at %s",
            getattr(settings, "MINIO_ENDPOINT", "unknown"),
            exc,
            SCAN_STORAGE_PATH,
        )
        _minio_available = False
        _minio_client = None
        return None


def is_minio_active() -> bool:
    """Return True if MinIO is configured and active."""
    return _get_minio_client() is not None


def save_bytes(
    data: bytes,
    relative_path: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Save bytes to storage (MinIO if available, otherwise local filesystem).
    Returns the accessible public URL of the file.
    """
    client = _get_minio_client()
    if client is not None:
        try:
            bucket = getattr(settings, "MINIO_BUCKET", "chess-academy")
            client.put_object(
                bucket_name=bucket,
                object_name=relative_path,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            public_base = getattr(settings, "MINIO_PUBLIC_URL", "http://localhost:9000")
            url = f"{public_base}/{bucket}/{relative_path}"
            logger.info("Saved to MinIO: %s (%d bytes)", url, len(data))
            return url
        except Exception as exc:
            logger.warning("MinIO upload failed for %s (%s), falling back to local", relative_path, exc)

    # Local storage fallback
    full_path = SCAN_STORAGE_PATH / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    url = f"{STORAGE_BASE_URL}/{relative_path}"
    logger.info("Saved to Local: %s (%d bytes)", url, len(data))
    return url


def get_file_bytes(file_url: str) -> bytes:
    """
    Retrieve file bytes from either MinIO or local storage based on the URL.
    """
    client = _get_minio_client()
    bucket = getattr(settings, "MINIO_BUCKET", "chess-academy")
    minio_prefix = f"/{bucket}/"

    if client is not None and minio_prefix in file_url:
        try:
            object_name = file_url.split(minio_prefix)[-1]
            response = client.get_object(bucket, object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except Exception as exc:
            logger.warning("Failed to read from MinIO for %s: %s", file_url, exc)

    # Local fallback
    relative = file_url.replace(STORAGE_BASE_URL + "/", "")
    full_path = SCAN_STORAGE_PATH / relative
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {full_path}")
    return full_path.read_bytes()
