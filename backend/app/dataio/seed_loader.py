"""Seed word loading from JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.feature_models import WordEntry


def load_seed_words(path: Path) -> list[WordEntry]:
    """Load normalized seed words from a JSONL file."""

    if not path.exists():
        raise FileNotFoundError(f"Seed word file not found: {path}")

    entries: list[WordEntry] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            entries.append(WordEntry.model_validate(payload))
    return entries
