"""Puzzle generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_generation_service
from app.schemas.api import GeneratedPuzzleResponse, PuzzleGenerationRequest
from app.services.generation_service import GenerationService

router = APIRouter()


@router.get("/sample", response_model=GeneratedPuzzleResponse)
def sample_puzzle(
    service: GenerationService = Depends(get_generation_service),
) -> GeneratedPuzzleResponse:
    return service.load_sample_puzzle()


@router.post("/generate", response_model=GeneratedPuzzleResponse)
def generate_puzzle(
    request: PuzzleGenerationRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GeneratedPuzzleResponse:
    return service.generate_puzzle(request)
