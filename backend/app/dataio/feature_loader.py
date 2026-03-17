"""Optional loading of precomputed feature records."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.feature_models import WordFeatures


def load_feature_records(path: Path) -> list[WordFeatures]:
    """Load feature records when a processed JSONL artifact exists."""

    if not path.exists():
        return []

    features: list[WordFeatures] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            features.append(WordFeatures.model_validate(json.loads(line)))
    return features
