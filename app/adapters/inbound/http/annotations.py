"""GET /annotations/{job_id} — tenant-scoped retrieval (US2/US3)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.adapters.inbound.http.auth import get_tenant
from app.application.services.get_annotation import AnnotationView

router = APIRouter()


def _serialize(view: AnnotationView) -> dict[str, Any]:
    return {
        "job_id": view.job_id,
        "status": view.status,
        "stage": view.stage,
        "result": asdict(view.result) if view.result is not None else None,
        "error": (
            {"stage": view.error.stage.value, "message": view.error.message}
            if view.error is not None
            else None
        ),
    }


@router.get("/annotations/{job_id}")
async def get_annotation(
    job_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant),
) -> dict[str, Any]:
    view = request.app.state.container.get_annotation.execute(tenant_id=tenant_id, job_id=job_id)
    if view is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return _serialize(view)
