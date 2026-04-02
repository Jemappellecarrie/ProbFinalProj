"""Identifier helpers used for reproducible demo artifacts."""

from __future__ import annotations

import hashlib
import json
import uuid


def new_id(prefix: str) -> str:
    """Return a compact identifier with a stable prefix."""

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def stable_id(prefix: str, *parts: object) -> str:
    """Return a content-derived identifier for deterministic artifacts."""

    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"
