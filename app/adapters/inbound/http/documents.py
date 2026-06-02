"""POST /documents — accept an upload, return 202 + job_id (US1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.adapters.inbound.http.auth import get_tenant
from app.adapters.inbound.http.uploads import safe_filename
from app.config import settings

router = APIRouter()


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant),
) -> dict[str, str]:
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported content-type: {file.content_type}",
        )
    # Read at most the cap + 1 byte so an oversized upload can't exhaust memory.
    content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty upload")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="file too large")
    job_id = request.app.state.container.ingest.execute(
        tenant_id=tenant_id,
        filename=safe_filename(file.filename),
        content_type=file.content_type,
        content=content,
    )
    return {"job_id": job_id, "status": "queued"}
