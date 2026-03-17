"""File-backed repository for seed words."""

from __future__ import annotations

from app.config.settings import Settings
from app.dataio.seed_loader import load_seed_words
from app.domain.protocols import WordRepository
from app.schemas.feature_models import WordEntry


class FileBackedWordRepository(WordRepository):
    """Load seed words from the repository's JSONL assets."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def list_entries(self) -> list[WordEntry]:
        return load_seed_words(self._settings.seed_words_path)
