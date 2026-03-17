"""Minimal logging configuration helper."""

from __future__ import annotations

import logging


def configure_logging(debug: bool) -> None:
    """Configure root logging once for local development and demo mode."""

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
