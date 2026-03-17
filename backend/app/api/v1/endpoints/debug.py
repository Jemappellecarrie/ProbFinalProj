"""Debug and developer-mode endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_runtime_settings
from app.config.settings import Settings
from app.schemas.api import DebugConfigResponse

router = APIRouter()


@router.get("/config", response_model=DebugConfigResponse)
def debug_config(settings: Settings = Depends(get_runtime_settings)) -> DebugConfigResponse:
    return DebugConfigResponse(
        app_name=settings.app_name,
        environment=settings.environment,
        demo_mode=settings.demo_mode,
        debug=settings.debug,
        cors_origins=settings.cors_origins,
        seed_words_path=str(settings.seed_words_path),
        processed_features_path=str(settings.processed_features_path),
    )
