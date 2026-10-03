"""
Signed file access — serves private local-storage files only when the URL carries
a valid, unexpired HMAC signature issued by storage_service.get_access_url().
(When MinIO is active, presigned MinIO URLs are used instead and this is bypassed.)
"""

import mimetypes

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import storage_service

router = APIRouter()

_ALLOWED_TYPES = {"image/png", "image/jpeg", "application/pdf"}


@router.get("/{expires}/{signature}/{path:path}")
async def get_signed_file(expires: int, signature: str, path: str):
    if not storage_service.verify_local_signature(path, expires, signature):
        raise HTTPException(403, detail="Invalid or expired link")
    file_path = storage_service.read_local_file(path)
    if file_path is None:
        raise HTTPException(404, detail="File not found")
    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    if media_type not in _ALLOWED_TYPES:
        raise HTTPException(404, detail="File not found")
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=600", "X-Content-Type-Options": "nosniff"},
    )
