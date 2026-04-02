"""Enumerations used across the generation pipeline."""

from __future__ import annotations

from enum import StrEnum


class GroupType(StrEnum):
    """High-level group generator families supported by the system."""

    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    PHONETIC = "phonetic"
    THEME = "theme"

    @classmethod
    def ordered(cls) -> list[GroupType]:
        return [cls.SEMANTIC, cls.LEXICAL, cls.PHONETIC, cls.THEME]


class GenerationMode(StrEnum):
    """Execution mode for pipeline components."""

    DEMO = "demo"
    HUMAN_MIXED = "human_mixed"


class VerificationDecision(StrEnum):
    """Stage 1 verification classes used by ranking and batch evaluation."""

    ACCEPT = "accept"
    BORDERLINE = "borderline"
    REJECT = "reject"


class RejectReasonCode(StrEnum):
    """Machine-readable rejection categories for filtering/verifier steps."""

    DUPLICATE_WORD = "duplicate_word"
    MISSING_GROUP_TYPE = "missing_group_type"
    INSUFFICIENT_GROUPS = "insufficient_groups"
    AMBIGUOUS_GROUPING = "ambiguous_grouping"
    LOW_COHERENCE = "low_coherence"
    UNSUPPORTED_MODE = "unsupported_mode"
