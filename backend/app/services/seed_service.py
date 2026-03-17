"""Seed asset helpers for scripts and future admin tooling."""

from __future__ import annotations

from app.config.settings import Settings
from app.dataio.feature_loader import load_feature_records
from app.dataio.seed_loader import load_seed_words


class SeedAssetService:
    """Provide lightweight summaries of seed and processed feature assets."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summarize(self) -> dict[str, int]:
        seed_words = load_seed_words(self._settings.seed_words_path)
        features = load_feature_records(self._settings.processed_features_path)
        return {"seed_word_count": len(seed_words), "processed_feature_count": len(features)}
