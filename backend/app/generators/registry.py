"""Registry helpers for group generator selection."""

from __future__ import annotations

from app.domain.protocols import GroupGenerator
from app.generators.lexical import MockLexicalGroupGenerator
from app.generators.phonetic import MockPhoneticGroupGenerator
from app.generators.semantic import MockSemanticGroupGenerator
from app.generators.theme import MockThemeGroupGenerator


def build_demo_generators() -> list[GroupGenerator]:
    """Return the default demo generator set in required group order."""

    return [
        MockSemanticGroupGenerator(),
        MockLexicalGroupGenerator(),
        MockPhoneticGroupGenerator(),
        MockThemeGroupGenerator(),
    ]
