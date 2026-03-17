"""Aggregate router for v1 endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import debug, health, metadata, puzzles

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
api_router.include_router(puzzles.router, prefix="/puzzles", tags=["puzzles"])
