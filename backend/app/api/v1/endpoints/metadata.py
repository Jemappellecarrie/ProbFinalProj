"""Metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_metadata_service
from app.schemas.api import GroupTypeMetadata
from app.services.metadata_service import MetadataService

router = APIRouter()


@router.get("/group-types", response_model=list[GroupTypeMetadata])
def group_types(service: MetadataService = Depends(get_metadata_service)) -> list[GroupTypeMetadata]:
    return service.list_group_types()
