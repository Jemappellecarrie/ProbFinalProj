"""Identifier helpers used for reproducible demo artifacts."""

from __future__ import annotations

import uuid


def new_id(prefix: str) -> str:
    """Return a compact identifier with a stable prefix."""

    return f"{prefix}_{uuid.uuid4().hex[:12]}"
