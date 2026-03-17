"""Metadata service for API endpoints and developer tooling."""

from __future__ import annotations

from app.core.enums import GroupType
from app.schemas.api import GroupTypeMetadata


class MetadataService:
    """Serve stable metadata about supported generator families."""

    def list_group_types(self) -> list[GroupTypeMetadata]:
        return [
            GroupTypeMetadata(
                type=GroupType.SEMANTIC,
                display_name="Semantic",
                description="Category-style group generation driven by meaning and taxonomy.",
            ),
            GroupTypeMetadata(
                type=GroupType.LEXICAL,
                display_name="Lexical",
                description="Orthographic or string-pattern grouping such as prefixes and suffixes.",
            ),
            GroupTypeMetadata(
                type=GroupType.PHONETIC,
                display_name="Phonetic",
                description="Sound-based or wordplay group generation.",
            ),
            GroupTypeMetadata(
                type=GroupType.THEME,
                display_name="Theme/Trivia",
                description="Theme-aware or curated trivia-style grouping.",
            ),
        ]
