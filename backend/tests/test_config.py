"""Configuration tests."""

from __future__ import annotations

from app.config.settings import Settings


def test_settings_resolve_repo_paths() -> None:
    settings = Settings()
    assert settings.repo_root.name == "ProbFinalProj"
    assert settings.seed_words_path.name == "seed_words.jsonl"
    assert settings.sample_puzzle_path.name == "sample_puzzle.json"
