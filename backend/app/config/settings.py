"""Application settings and path resolution."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central runtime configuration for backend services and demo wiring."""

    app_name: str = Field(default="Connections Puzzle Generator")
    environment: str = Field(default="development")
    demo_mode: bool = Field(default=True)
    debug: bool = Field(default=True)
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_prefix="CONNECTIONS_",
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
    )

    @computed_field  # type: ignore[misc]
    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @computed_field  # type: ignore[misc]
    @property
    def data_dir(self) -> Path:
        return self.repo_root / "data"

    @computed_field  # type: ignore[misc]
    @property
    def seed_words_path(self) -> Path:
        return self.data_dir / "seed" / "seed_words.jsonl"

    @computed_field  # type: ignore[misc]
    @property
    def demo_groups_path(self) -> Path:
        return self.data_dir / "seed" / "demo_groups.json"

    @computed_field  # type: ignore[misc]
    @property
    def processed_features_path(self) -> Path:
        return self.data_dir / "processed" / "demo_word_features.jsonl"

    @computed_field  # type: ignore[misc]
    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "processed" / "connections_demo.sqlite3"

    @computed_field  # type: ignore[misc]
    @property
    def eval_runs_dir(self) -> Path:
        return self.data_dir / "processed" / "eval_runs"

    @computed_field  # type: ignore[misc]
    @property
    def sample_puzzle_path(self) -> Path:
        return self.data_dir / "samples" / "sample_puzzle.json"

    @computed_field  # type: ignore[misc]
    @property
    def sample_trace_path(self) -> Path:
        return self.data_dir / "samples" / "sample_trace.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for dependency injection."""

    return Settings()
