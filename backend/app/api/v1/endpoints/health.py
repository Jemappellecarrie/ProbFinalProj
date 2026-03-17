"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_runtime_settings
from app.config.settings import Settings
from app.schemas.api import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health(settings: Settings = Depends(get_runtime_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        demo_mode=settings.demo_mode,
    )
