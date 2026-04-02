#!/usr/bin/env python3
# ruff: noqa: E402
"""Build processed demo feature artifacts from seed data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.settings import Settings
from app.dataio.sqlite_store import SQLiteWordFeatureStore
from app.dataio.seed_loader import load_seed_words
from app.features.mock_extractor import MockWordFeatureExtractor


def main() -> None:
    settings = Settings()
    seed_words = load_seed_words(settings.seed_words_path)
    extractor = MockWordFeatureExtractor()
    features = extractor.extract_features(seed_words)

    settings.processed_features_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.processed_features_path.open("w", encoding="utf-8") as handle:
        for record in features:
            handle.write(json.dumps(record.model_dump(mode="json")))
            handle.write("\n")

    store = SQLiteWordFeatureStore(settings.sqlite_path)
    store.upsert(features)

    print(
        json.dumps(
            {
                "seed_word_count": len(seed_words),
                "feature_record_count": len(features),
                "processed_features_path": str(settings.processed_features_path),
                "sqlite_path": str(settings.sqlite_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
