"""Deterministic editorial-family helpers for ranking and evaluation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

from app.core.enums import GroupType
from app.features.semantic_baseline import normalize_signal
from app.utils.ids import stable_id

BROAD_THEME_LABELS = {"gemstones", "planets"}
SURFACE_LEXICAL_PATTERN_TYPES = {"shared_prefix", "shared_suffix", "shared_substring"}
SURFACE_PHONETIC_PATTERN_TYPES = {"perfect_rhyme"}
HIGH_PAYOFF_PHONETIC_PATTERN_TYPES = {"exact_homophone"}


def _group_type_value(group: Any) -> str:
    group_type = getattr(group, "group_type", None)
    if isinstance(group_type, GroupType):
        return group_type.value
    return str(group_type or "")


def _group_label(group: Any) -> str:
    return str(getattr(group, "label", "") or "")


def _group_metadata(group: Any) -> dict[str, Any]:
    metadata = getattr(group, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _label_token_count(label: str) -> int:
    return len([token for token in label.replace("-", " ").replace('"', " ").split() if token])


def group_surface_wordplay_score(group: Any) -> float:
    """Return a coarse score for how surface-driven the group's wordplay is."""

    group_type = _group_type_value(group)
    metadata = _group_metadata(group)
    if group_type == GroupType.LEXICAL.value:
        pattern_type = metadata.get("pattern_type", "")
        if pattern_type == "shared_substring":
            return 1.0
        if pattern_type in SURFACE_LEXICAL_PATTERN_TYPES:
            return 0.9
        return 0.55
    if group_type == GroupType.PHONETIC.value:
        phonetic_type = metadata.get("phonetic_pattern_type", "")
        if phonetic_type in SURFACE_PHONETIC_PATTERN_TYPES:
            return 0.95
        if phonetic_type in HIGH_PAYOFF_PHONETIC_PATTERN_TYPES:
            return 0.35
        return 0.6
    return 0.0


def group_earned_wordplay_score(group: Any) -> float:
    """Return a coarse score for how editorially earned the wordplay feels."""

    group_type = _group_type_value(group)
    metadata = _group_metadata(group)
    if group_type == GroupType.PHONETIC.value:
        phonetic_type = metadata.get("phonetic_pattern_type", "")
        if phonetic_type in HIGH_PAYOFF_PHONETIC_PATTERN_TYPES:
            return 1.0
        if phonetic_type in SURFACE_PHONETIC_PATTERN_TYPES:
            return 0.45
        return 0.55
    if group_type == GroupType.LEXICAL.value:
        pattern_type = metadata.get("pattern_type", "")
        if pattern_type in SURFACE_LEXICAL_PATTERN_TYPES:
            return 0.2
        return 0.4
    return 0.0


def group_microtheme_smallness(group: Any) -> float:
    """Return a heuristic risk score for overly small curated themes."""

    if _group_type_value(group) != GroupType.THEME.value:
        return 0.0
    metadata = _group_metadata(group)
    normalized_label = metadata.get("normalized_label", normalize_signal(_group_label(group)))
    if normalized_label in BROAD_THEME_LABELS:
        return 0.15
    if _label_token_count(_group_label(group)) >= 2:
        return 0.85
    return 0.55


def group_family_signature(group: Any) -> str:
    """Return a normalized editorial family signature for one group."""

    group_type = _group_type_value(group)
    metadata = _group_metadata(group)
    normalized_label = metadata.get("normalized_label", normalize_signal(_group_label(group)))

    if group_type == GroupType.SEMANTIC.value:
        return str(metadata.get("rule_signature") or f"semantic:{normalized_label}")

    if group_type == GroupType.THEME.value:
        theme_name = metadata.get("theme_name")
        return (
            f"theme:{theme_name}"
            if theme_name
            else str(metadata.get("rule_signature") or f"theme:{normalized_label}")
        )

    if group_type == GroupType.LEXICAL.value:
        pattern_type = metadata.get("pattern_type", "lexical_pattern")
        pattern = metadata.get("normalized_pattern") or normalized_label
        return f"lexical:{pattern_type}:{pattern}"

    if group_type == GroupType.PHONETIC.value:
        phonetic_type = metadata.get("phonetic_pattern_type", "phonetic_wordplay")
        normalized_signature = metadata.get("normalized_phonetic_signature")
        if isinstance(normalized_signature, str) and normalized_signature.startswith(
            f"{phonetic_type}:"
        ):
            return f"phonetic:{normalized_signature}"
        pattern = normalized_signature or normalized_label
        return f"phonetic:{phonetic_type}:{pattern}"

    return f"{group_type}:{normalized_label}"


def build_editorial_family_metadata(groups: Sequence[Any]) -> dict[str, object]:
    """Build deterministic family metadata for one puzzle board."""

    family_signatures = [group_family_signature(group) for group in groups]
    group_types = [_group_type_value(group) for group in groups]
    theme_family_signatures = [
        signature
        for group, signature in zip(groups, family_signatures, strict=True)
        if _group_type_value(group) == GroupType.THEME.value
    ]
    surface_wordplay_family_signatures = [
        signature
        for group, signature in zip(groups, family_signatures, strict=True)
        if group_surface_wordplay_score(group) >= 0.7
    ]
    low_payoff_surface_wordplay_families = [
        signature
        for group, signature in zip(groups, family_signatures, strict=True)
        if group_surface_wordplay_score(group) >= 0.7 and group_earned_wordplay_score(group) < 0.5
    ]
    microtheme_family_signatures = [
        signature
        for group, signature in zip(groups, family_signatures, strict=True)
        if group_microtheme_smallness(group) >= 0.5
    ]

    flags: list[str] = []
    unique_group_type_count = len(set(group_types))
    if (
        unique_group_type_count >= 3
        and theme_family_signatures
        and len(surface_wordplay_family_signatures) >= 2
    ):
        flags.append("formulaic_mixed_template")
    if len(low_payoff_surface_wordplay_families) >= 2:
        flags.append("surface_wordplay_heavy")
    if microtheme_family_signatures:
        flags.append("microtheme_trivia_smallness")

    mechanism_signature = "+".join(sorted(Counter(group_types)))
    board_family_signature = stable_id("board_family", sorted(family_signatures))
    editorial_family_signature = stable_id(
        "editorial_family",
        mechanism_signature,
        sorted(theme_family_signatures),
        sorted(low_payoff_surface_wordplay_families),
        sorted(flags),
    )
    return {
        "group_family_signatures": family_signatures,
        "board_family_signature": board_family_signature,
        "editorial_family_signature": editorial_family_signature,
        "theme_family_signatures": theme_family_signatures,
        "surface_wordplay_family_signatures": surface_wordplay_family_signatures,
        "low_payoff_surface_wordplay_families": low_payoff_surface_wordplay_families,
        "microtheme_family_signatures": microtheme_family_signatures,
        "editorial_flags": flags,
    }


def record_group_family_signatures(record: Any) -> list[str]:
    """Return persisted group family signatures, with a coarse fallback."""

    existing = getattr(record, "group_family_signatures", None)
    if existing:
        return list(existing)

    labels = list(getattr(record, "group_labels", []) or [])
    group_types = list(getattr(record, "group_types", []) or [])
    signatures: list[str] = []
    for group_type, label in zip(group_types, labels, strict=False):
        signatures.append(f"{group_type}:{normalize_signal(label)}")
    return signatures


def record_board_family_signature(record: Any) -> str:
    existing = getattr(record, "board_family_signature", None)
    if existing:
        return str(existing)
    return stable_id("board_family", sorted(record_group_family_signatures(record)))


def record_editorial_family_signature(record: Any) -> str:
    existing = getattr(record, "editorial_family_signature", None)
    if existing:
        return str(existing)
    theme_signatures = record_theme_family_signatures(record)
    surface_signatures = record_surface_wordplay_family_signatures(record)
    flags = sorted(record_editorial_flags(record))
    mechanism_signature = "+".join(sorted(set(getattr(record, "group_types", []) or [])))
    return stable_id(
        "editorial_family",
        mechanism_signature,
        sorted(theme_signatures),
        sorted(surface_signatures),
        flags,
    )


def record_theme_family_signatures(record: Any) -> list[str]:
    existing = getattr(record, "theme_family_signatures", None)
    if existing:
        return list(existing)
    return [
        signature
        for signature in record_group_family_signatures(record)
        if signature.startswith("theme:")
    ]


def record_surface_wordplay_family_signatures(record: Any) -> list[str]:
    existing = getattr(record, "surface_wordplay_family_signatures", None)
    if existing:
        return list(existing)
    return [
        signature
        for signature in record_group_family_signatures(record)
        if signature.startswith("lexical:") or signature.startswith("phonetic:")
    ]


def record_editorial_flags(record: Any) -> list[str]:
    existing = getattr(record, "editorial_flags", None)
    if existing:
        return sorted(set(existing))
    style_analysis = getattr(record, "style_analysis", None)
    if (
        style_analysis is not None
        and getattr(style_analysis, "board_style_summary", None) is not None
    ):
        board_style_summary = style_analysis.board_style_summary
        explicit_flags = list(getattr(board_style_summary, "editorial_flags", []) or [])
        if explicit_flags:
            return sorted(set(explicit_flags))
        metrics = dict(getattr(board_style_summary, "metrics", {}) or {})
        inferred_flags: list[str] = []
        if float(metrics.get("formulaic_mix_score", 0.0)) >= 0.65:
            inferred_flags.append("formulaic_mixed_template")
        if float(metrics.get("microtheme_smallness", 0.0)) >= 0.65:
            inferred_flags.append("microtheme_trivia_smallness")
        return sorted(set(inferred_flags))
    return []
