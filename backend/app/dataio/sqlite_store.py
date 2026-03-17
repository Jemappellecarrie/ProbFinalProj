"""SQLite-backed storage for future offline feature indexing."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.schemas.feature_models import WordFeatures


class SQLiteWordFeatureStore:
    """Very small SQLite store used for demo bootstrapping and future indexing work."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        """Create storage tables and indexes if they do not exist."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS word_features (
                    word_id TEXT PRIMARY KEY,
                    normalized TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_word_features_normalized ON word_features(normalized)"
            )

    def upsert(self, records: list[WordFeatures]) -> None:
        """Persist feature records as JSON blobs for later retrieval."""

        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.executemany(
                """
                INSERT INTO word_features (word_id, normalized, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(word_id) DO UPDATE SET
                    normalized = excluded.normalized,
                    payload_json = excluded.payload_json
                """,
                [
                    (record.word_id, record.normalized, record.model_dump_json())
                    for record in records
                ],
            )

    def fetch_all(self) -> list[WordFeatures]:
        """Load all stored feature records."""

        if not self.path.exists():
            return []

        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT payload_json FROM word_features").fetchall()
        return [WordFeatures.model_validate(json.loads(row[0])) for row in rows]
