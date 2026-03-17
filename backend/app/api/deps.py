"""Dependency injection helpers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.services.generation_service import GenerationService
from app.services.metadata_service import MetadataService


@lru_cache(maxsize=1)
def get_generation_service() -> GenerationService:
    return GenerationService(get_settings())


@lru_cache(maxsize=1)
def get_metadata_service() -> MetadataService:
    return MetadataService()


def get_runtime_settings() -> Settings:
    return get_settings()
