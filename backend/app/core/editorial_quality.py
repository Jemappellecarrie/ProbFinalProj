"""Deterministic editorial-family helpers for ranking and evaluation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

from app.core.enums import GroupType
from app.features.semantic_baseline import normalize_signal
from app.utils.ids import stable_id

BROAD_THEME_LABELS = {"gemstones", "planets"}
NARROW_CURATED_THEME_NAMES = {
    "pac_man_ghosts",
    "teenage_mutant_ninja_turtles",
}
SURFACE_LEXICAL_PATTERN_TYPES = {"shared_prefix", "shared_suffix", "shared_substring"}
SURFACE_PHONETIC_PATTERN_TYPES = {"perfect_rhyme"}
HIGH_PAYOFF_PHONETIC_PATTERN_TYPES = {"exact_homophone"}
TAXONOMY_LABEL_STARTS = ("starts with", "starting with", "ends with", "ending in", "contains")
TAXONOMY_LABEL_CONTAINS = ("rhymes with", "rhyming with")
RUN_FAMILY_BUCKETS = ("group", "board", "editorial", "label", "theme", "surface", "template")
WINNER_FAMILY_BUCKETS = ("board", "editorial", "label", "theme", "surface", "template")
WINNER_RECENT_HISTORY_LIMIT = 24
WINNER_RECENT_WINDOW = 6


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


def _uppercase_pattern(pattern: Any) -> str:
    return str(pattern or "").replace("-", " ").strip().upper()


def _is_blank_frame_label(label: str) -> bool:
    return "___" in label or label.count("__") >= 2


def _blank_frame_label(pattern: str, *, mode: str) -> str:
    rendered = _uppercase_pattern(pattern)
    if not rendered:
        return rendered
    if mode == "prefix":
        return f"{rendered}___"
    if mode == "suffix":
        return f"___{rendered}"
    return f"__{rendered}__"


def _exact_homophone_reference(group: Any) -> str:
    metadata = _group_metadata(group)
    evidence = metadata.get("evidence", {})
    if isinstance(evidence, dict):
        membership = evidence.get("pronunciation_membership", [])
        if isinstance(membership, list) and membership:
            word = membership[0].get("word")
            if isinstance(word, str) and word:
                return word.upper()
    words = list(getattr(group, "words", []) or [])
    return sorted(str(word).upper() for word in words)[0] if words else _group_label(group).upper()


def group_surface_wordplay_score(group: Any) -> float:
    """Return a coarse score for how surface-driven the group's wordplay is."""

    group_type = _group_type_value(group)
    metadata = _group_metadata(group)
    if group_type == GroupType.LEXICAL.value:
        pattern_type = metadata.get("pattern_type", "")
        if pattern_type == "shared_substring":
            return 1.0
        if pattern_type in SURFACE_LEXICAL_PATTERN_TYPES:
            return 0.95
        return 0.55
    if group_type == GroupType.PHONETIC.value:
        phonetic_type = metadata.get("phonetic_pattern_type", "")
        if phonetic_type in SURFACE_PHONETIC_PATTERN_TYPES:
            return 1.0
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
            return 0.3
        return 0.55
    if group_type == GroupType.LEXICAL.value:
        pattern_type = metadata.get("pattern_type", "")
        if pattern_type in SURFACE_LEXICAL_PATTERN_TYPES:
            return 0.15
        return 0.4
    return 0.0


def group_microtheme_smallness(group: Any) -> float:
    """Return a heuristic risk score for overly small curated themes."""

    metadata = _group_metadata(group)
    normalized_label = metadata.get("normalized_label", normalize_signal(_group_label(group)))
    theme_name = normalize_signal(str(metadata.get("theme_name", "")))
    group_type = _group_type_value(group)
    if group_type != GroupType.THEME.value:
        return 0.0
    if normalized_label in BROAD_THEME_LABELS or theme_name in {
        "classical_planets",
        "common_gemstones",
    }:
        return 0.15
    if theme_name in NARROW_CURATED_THEME_NAMES:
        return 1.0
    if _label_token_count(_group_label(group)) >= 2:
        return 0.95
    return 0.65


def group_phrase_template_payoff_score(group: Any) -> float:
    """Return a coarse estimate of clue or phrase payoff beyond raw pattern presence."""

    group_type = _group_type_value(group)
    metadata = _group_metadata(group)
    label = _group_label(group)
    if group_type == GroupType.PHONETIC.value:
        phonetic_type = metadata.get("phonetic_pattern_type", "")
        if phonetic_type in HIGH_PAYOFF_PHONETIC_PATTERN_TYPES:
            return 0.9
        if phonetic_type in SURFACE_PHONETIC_PATTERN_TYPES:
            return 0.08 if _is_blank_frame_label(label) else 0.12
        return 0.35
    if group_type == GroupType.LEXICAL.value:
        pattern_type = metadata.get("pattern_type", "")
        if pattern_type == "shared_substring":
            return 0.06
        if pattern_type == "shared_suffix":
            return 0.08 if _is_blank_frame_label(label) else 0.1
        if pattern_type == "shared_prefix":
            return 0.1 if _is_blank_frame_label(label) else 0.14
        return 0.25
    if group_type == GroupType.THEME.value:
        return 0.4 if group_microtheme_smallness(group) < 0.5 else 0.12
    if group_type == GroupType.SEMANTIC.value:
        return 0.45 if _label_token_count(label) <= 3 else 0.35
    return 0.0


def group_is_clue_like_label(group: Any) -> bool:
    """Return whether the label reads like a clue or natural editorial heading."""

    group_type = _group_type_value(group)
    metadata = _group_metadata(group)
    lowered = _group_label(group).lower()
    if group_type == GroupType.PHONETIC.value and metadata.get(
        "phonetic_pattern_type"
    ) in HIGH_PAYOFF_PHONETIC_PATTERN_TYPES:
        return True
    if _is_blank_frame_label(_group_label(group)):
        return True
    if '"' in lowered and "contains" not in lowered:
        return True
    return False


def group_is_taxonomy_like_label(group: Any) -> bool:
    """Return whether the label reads like generator taxonomy rather than clueing."""

    lowered = _group_label(group).lower()
    metadata = _group_metadata(group)
    if _is_blank_frame_label(_group_label(group)):
        return False
    if lowered.startswith(TAXONOMY_LABEL_STARTS) or any(
        token in lowered for token in TAXONOMY_LABEL_CONTAINS
    ):
        return True
    if metadata.get("pattern_type") in SURFACE_LEXICAL_PATTERN_TYPES:
        return True
    return bool(metadata.get("phonetic_pattern_type") in SURFACE_PHONETIC_PATTERN_TYPES)


def polish_group_label(group: Any) -> Any:
    """Return a conservatively polished copy of a group label when wording is too technical."""

    metadata = dict(_group_metadata(group))
    original_label = _group_label(group)
    polished_label = original_label
    polish_reason: str | None = None

    if _group_type_value(group) == GroupType.LEXICAL.value:
        pattern_type = str(metadata.get("pattern_type", "") or "")
        rendered = _uppercase_pattern(metadata.get("normalized_pattern"))
        if pattern_type == "shared_prefix" and rendered:
            polished_label = _blank_frame_label(rendered, mode="prefix")
            polish_reason = "shared_prefix_label_polish"
        elif pattern_type == "shared_suffix" and rendered:
            polished_label = _blank_frame_label(rendered, mode="suffix")
            polish_reason = "shared_suffix_label_polish"
        elif pattern_type == "shared_substring" and rendered:
            polished_label = _blank_frame_label(rendered, mode="substring")
            polish_reason = "shared_substring_label_polish"
    elif _group_type_value(group) == GroupType.PHONETIC.value:
        phonetic_type = str(metadata.get("phonetic_pattern_type", "") or "")
        if phonetic_type in HIGH_PAYOFF_PHONETIC_PATTERN_TYPES:
            polished_label = f'Sounds like "{_exact_homophone_reference(group)}"'
            polish_reason = "exact_homophone_label_polish"
        elif phonetic_type in SURFACE_PHONETIC_PATTERN_TYPES:
            spelling_hint = _uppercase_pattern(metadata.get("spelling_rhyme_hint"))
            if spelling_hint:
                polished_label = _blank_frame_label(spelling_hint, mode="suffix")
                polish_reason = "perfect_rhyme_label_polish"

    if polished_label == original_label:
        return group

    metadata["original_label"] = original_label
    metadata["normalized_label"] = normalize_signal(polished_label)
    metadata["label_polish_applied"] = True
    metadata["label_polish_reason"] = polish_reason
    model_copy = getattr(group, "model_copy", None)
    if callable(model_copy):
        return model_copy(update={"label": polished_label, "metadata": metadata})

    group.label = polished_label
    group.metadata = metadata
    return group


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
    label_signatures = [
        normalize_signal(_group_metadata(group).get("normalized_label", _group_label(group)))
        for group in groups
    ]
    group_types = [_group_type_value(group) for group in groups]
    group_type_counts = Counter(group_types)
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
        if group_surface_wordplay_score(group) >= 0.7
        and max(
            group_earned_wordplay_score(group),
            group_phrase_template_payoff_score(group),
        )
        < 0.45
    ]
    microtheme_family_signatures = [
        signature
        for group, signature in zip(groups, family_signatures, strict=True)
        if group_microtheme_smallness(group) >= 0.5
    ]
    lexical_group_count = group_type_counts.get(GroupType.LEXICAL.value, 0)
    phonetic_group_count = group_type_counts.get(GroupType.PHONETIC.value, 0)
    semantic_group_count = group_type_counts.get(GroupType.SEMANTIC.value, 0)
    theme_group_count = group_type_counts.get(GroupType.THEME.value, 0)
    wordplay_group_count = lexical_group_count + phonetic_group_count
    surface_wordplay_group_count = len(surface_wordplay_family_signatures)
    semantic_majority_board = (
        semantic_group_count >= 3
        or (
            semantic_group_count >= 2
            and wordplay_group_count <= 1
            and theme_group_count <= 1
        )
    )
    balanced_mixed_board = (
        semantic_group_count <= 2
        and theme_group_count >= 1
        and wordplay_group_count >= 1
        and len(set(group_types)) >= 3
    )
    microtheme_plus_wordplay = bool(microtheme_family_signatures and surface_wordplay_group_count)
    mechanism_template_signature = stable_id(
        "template",
        f"s{semantic_group_count}",
        f"l{lexical_group_count}",
        f"p{phonetic_group_count}",
        f"t{theme_group_count}",
        f"surface{surface_wordplay_group_count}",
        f"micro{len(microtheme_family_signatures)}",
        "semantic_majority" if semantic_majority_board else "non_semantic_majority",
        "balanced_mixed" if balanced_mixed_board else "not_balanced_mixed",
        "micro_plus_wordplay" if microtheme_plus_wordplay else "no_micro_plus_wordplay",
    )

    flags: list[str] = []
    if balanced_mixed_board and theme_family_signatures and surface_wordplay_group_count >= 1:
        flags.append("formulaic_mixed_template")
    if len(low_payoff_surface_wordplay_families) >= 2:
        flags.append("surface_wordplay_heavy")
    if microtheme_family_signatures:
        flags.append("microtheme_trivia_smallness")
    if semantic_majority_board:
        flags.append("semantic_majority_board")
    if balanced_mixed_board:
        flags.append("balanced_mixed_board")
    if microtheme_plus_wordplay:
        flags.append("microtheme_plus_surface_wordplay")

    mechanism_signature = "+".join(sorted(Counter(group_types)))
    board_family_signature = stable_id("board_family", sorted(family_signatures))
    label_family_signature = stable_id("label_family", sorted(label_signatures))
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
        "label_family_signature": label_family_signature,
        "editorial_family_signature": editorial_family_signature,
        "theme_family_signatures": theme_family_signatures,
        "surface_wordplay_family_signatures": surface_wordplay_family_signatures,
        "low_payoff_surface_wordplay_families": low_payoff_surface_wordplay_families,
        "microtheme_family_signatures": microtheme_family_signatures,
        "mechanism_template_signature": mechanism_template_signature,
        "semantic_group_count": semantic_group_count,
        "lexical_group_count": lexical_group_count,
        "phonetic_group_count": phonetic_group_count,
        "theme_group_count": theme_group_count,
        "wordplay_group_count": wordplay_group_count,
        "surface_wordplay_group_count": surface_wordplay_group_count,
        "semantic_majority_board": semantic_majority_board,
        "balanced_mixed_board": balanced_mixed_board,
        "microtheme_plus_wordplay": microtheme_plus_wordplay,
        "editorial_flags": flags,
    }


def empty_run_family_accounting() -> dict[str, dict[str, dict[str, int]] | dict[str, int]]:
    """Return the default run-level family-accounting payload."""

    return {
        "family_proposal_count_by_run": {bucket: {} for bucket in RUN_FAMILY_BUCKETS},
        "family_retention_count_by_run": {bucket: {} for bucket in RUN_FAMILY_BUCKETS},
        "winner_family_count_by_run": {bucket: {} for bucket in WINNER_FAMILY_BUCKETS},
        "winner_recent_history": {bucket: [] for bucket in WINNER_FAMILY_BUCKETS},
        "family_suppression_events": {},
        "per_family_cap_hits": {},
        "winner_suppression_events": {},
    }


def ensure_run_family_accounting(state: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a possibly sparse run-level accounting payload."""

    normalized = dict(state or {})
    normalized.setdefault(
        "family_proposal_count_by_run",
        {bucket: {} for bucket in RUN_FAMILY_BUCKETS},
    )
    normalized.setdefault(
        "family_retention_count_by_run",
        {bucket: {} for bucket in RUN_FAMILY_BUCKETS},
    )
    normalized.setdefault(
        "winner_family_count_by_run",
        {bucket: {} for bucket in WINNER_FAMILY_BUCKETS},
    )
    normalized.setdefault(
        "winner_recent_history",
        {bucket: [] for bucket in WINNER_FAMILY_BUCKETS},
    )
    normalized.setdefault("family_suppression_events", {})
    normalized.setdefault("per_family_cap_hits", {})
    normalized.setdefault("winner_suppression_events", {})
    for parent_key in (
        "family_proposal_count_by_run",
        "family_retention_count_by_run",
        "winner_family_count_by_run",
    ):
        container = normalized.get(parent_key, {})
        if not isinstance(container, dict):
            container = {}
            normalized[parent_key] = container
        expected_buckets = RUN_FAMILY_BUCKETS
        if parent_key == "winner_family_count_by_run":
            expected_buckets = WINNER_FAMILY_BUCKETS
        for bucket in expected_buckets:
            bucket_counts = container.get(bucket)
            if not isinstance(bucket_counts, dict):
                container[bucket] = {}
    history = normalized.get("winner_recent_history", {})
    if not isinstance(history, dict):
        history = {}
        normalized["winner_recent_history"] = history
    for bucket in WINNER_FAMILY_BUCKETS:
        bucket_history = history.get(bucket)
        if not isinstance(bucket_history, list):
            history[bucket] = []
    return normalized


def _increment_nested_counter(
    mapping: dict[str, dict[str, int]],
    bucket: str,
    signature: str | None,
    amount: int = 1,
) -> None:
    if not signature:
        return
    bucket_counts = mapping.setdefault(bucket, {})
    bucket_counts[signature] = int(bucket_counts.get(signature, 0)) + amount


def _increment_counter(mapping: dict[str, int], key: str | None, amount: int = 1) -> None:
    if not key:
        return
    mapping[key] = int(mapping.get(key, 0)) + amount


def run_family_count(
    state: dict[str, Any] | None,
    *,
    parent_key: str,
    bucket: str,
    signature: str | None,
) -> int:
    normalized = ensure_run_family_accounting(state)
    parent = normalized.get(parent_key, {})
    if not isinstance(parent, dict):
        return 0
    bucket_counts = parent.get(bucket, {})
    if not isinstance(bucket_counts, dict) or not signature:
        return 0
    return int(bucket_counts.get(signature, 0))


def record_run_family_event(
    state: dict[str, Any] | None,
    *,
    parent_key: str,
    bucket: str,
    signature: str | None,
    amount: int = 1,
) -> dict[str, Any]:
    normalized = ensure_run_family_accounting(state)
    _increment_nested_counter(normalized[parent_key], bucket, signature, amount=amount)  # type: ignore[index]
    return normalized


def record_run_suppression(
    state: dict[str, Any] | None,
    *,
    reason: str,
    signature: str | None = None,
) -> dict[str, Any]:
    normalized = ensure_run_family_accounting(state)
    label = f"{reason}:{signature}" if signature else reason
    _increment_counter(normalized["family_suppression_events"], label)
    return normalized


def record_run_cap_hit(
    state: dict[str, Any] | None,
    *,
    bucket: str,
    signature: str | None,
) -> dict[str, Any]:
    normalized = ensure_run_family_accounting(state)
    label = f"{bucket}:{signature}" if signature else bucket
    _increment_counter(normalized["per_family_cap_hits"], label)
    return normalized


def record_run_winner_suppression(
    state: dict[str, Any] | None,
    *,
    reason: str,
    signature: str | None = None,
) -> dict[str, Any]:
    normalized = ensure_run_family_accounting(state)
    label = f"{reason}:{signature}" if signature else reason
    _increment_counter(normalized["winner_suppression_events"], label)
    return normalized


def recent_winner_history_count(
    state: dict[str, Any] | None,
    *,
    bucket: str,
    signature: str | None,
    window: int = WINNER_RECENT_WINDOW,
) -> int:
    normalized = ensure_run_family_accounting(state)
    history = normalized.get("winner_recent_history", {})
    if not isinstance(history, dict) or not signature:
        return 0
    bucket_history = history.get(bucket, [])
    if not isinstance(bucket_history, list):
        return 0
    return sum(1 for item in bucket_history[-window:] if item == signature)


def record_recent_winner_signature(
    state: dict[str, Any] | None,
    *,
    bucket: str,
    signature: str | None,
    limit: int = WINNER_RECENT_HISTORY_LIMIT,
) -> dict[str, Any]:
    normalized = ensure_run_family_accounting(state)
    if not signature:
        return normalized
    history = normalized["winner_recent_history"].setdefault(bucket, [])
    if not isinstance(history, list):
        history = []
        normalized["winner_recent_history"][bucket] = history
    history.append(signature)
    if len(history) > limit:
        del history[:-limit]
    return normalized


def record_mechanism_template_signature(record: Any) -> str:
    existing = getattr(record, "mechanism_template_signature", None)
    if existing:
        return str(existing)
    group_types = list(getattr(record, "group_types", []) or [])
    counts = Counter(group_types)
    theme_family_signatures = record_theme_family_signatures(record)
    surface_wordplay_family_signatures = record_surface_wordplay_family_signatures(record)
    editorial_flags = set(record_editorial_flags(record))
    semantic_group_count = counts.get(GroupType.SEMANTIC.value, 0)
    lexical_group_count = counts.get(GroupType.LEXICAL.value, 0)
    phonetic_group_count = counts.get(GroupType.PHONETIC.value, 0)
    theme_group_count = counts.get(GroupType.THEME.value, 0)
    wordplay_group_count = lexical_group_count + phonetic_group_count
    semantic_majority_board = (
        semantic_group_count >= 3
        or (
            semantic_group_count >= 2
            and wordplay_group_count <= 1
            and theme_group_count <= 1
        )
    )
    balanced_mixed_board = (
        semantic_group_count <= 2
        and theme_group_count >= 1
        and wordplay_group_count >= 1
        and len(set(group_types)) >= 3
    )
    return stable_id(
        "template",
        f"s{semantic_group_count}",
        f"l{lexical_group_count}",
        f"p{phonetic_group_count}",
        f"t{theme_group_count}",
        f"surface{len(surface_wordplay_family_signatures)}",
        f"micro{1 if 'microtheme_trivia_smallness' in editorial_flags else 0}",
        "semantic_majority" if semantic_majority_board else "non_semantic_majority",
        "balanced_mixed" if balanced_mixed_board else "not_balanced_mixed",
        "micro_plus_wordplay"
        if theme_family_signatures and surface_wordplay_family_signatures
        else "no_micro_plus_wordplay",
    )


def record_semantic_majority_board(record: Any) -> bool:
    style_analysis = getattr(record, "style_analysis", None)
    if (
        style_analysis is not None
        and getattr(style_analysis, "board_style_summary", None) is not None
    ):
        metrics = dict(getattr(style_analysis.board_style_summary, "metrics", {}) or {})
        semantic_group_count = int(metrics.get("semantic_group_count", 0))
        wordplay_group_count = int(metrics.get("wordplay_group_count", 0))
        theme_group_count = int(metrics.get("theme_group_count", 0))
        return semantic_group_count >= 3 or (
            semantic_group_count >= 2
            and wordplay_group_count <= 1
            and theme_group_count <= 1
        )
    counts = Counter(getattr(record, "group_types", []) or [])
    semantic_group_count = counts.get(GroupType.SEMANTIC.value, 0)
    wordplay_group_count = counts.get(GroupType.LEXICAL.value, 0) + counts.get(
        GroupType.PHONETIC.value, 0
    )
    theme_group_count = counts.get(GroupType.THEME.value, 0)
    return semantic_group_count >= 3 or (
        semantic_group_count >= 2
        and wordplay_group_count <= 1
        and theme_group_count <= 1
    )


def record_balanced_mixed_board(record: Any) -> bool:
    style_analysis = getattr(record, "style_analysis", None)
    if (
        style_analysis is not None
        and getattr(style_analysis, "board_style_summary", None) is not None
    ):
        metrics = dict(getattr(style_analysis.board_style_summary, "metrics", {}) or {})
        semantic_group_count = int(metrics.get("semantic_group_count", 0))
        wordplay_group_count = int(metrics.get("wordplay_group_count", 0))
        theme_group_count = int(metrics.get("theme_group_count", 0))
        unique_group_type_count = int(metrics.get("unique_group_type_count", 0))
        return (
            semantic_group_count <= 2
            and theme_group_count >= 1
            and wordplay_group_count >= 1
            and unique_group_type_count >= 3
        )
    counts = Counter(getattr(record, "group_types", []) or [])
    semantic_group_count = counts.get(GroupType.SEMANTIC.value, 0)
    wordplay_group_count = counts.get(GroupType.LEXICAL.value, 0) + counts.get(
        GroupType.PHONETIC.value, 0
    )
    theme_group_count = counts.get(GroupType.THEME.value, 0)
    return (
        semantic_group_count <= 2
        and theme_group_count >= 1
        and wordplay_group_count >= 1
        and len(counts) >= 3
    )


def record_microtheme_plus_wordplay(record: Any) -> bool:
    flags = set(record_editorial_flags(record))
    if "microtheme_plus_surface_wordplay" in flags:
        return True
    return bool(
        record_theme_family_signatures(record)
        and record_surface_wordplay_family_signatures(record)
    )


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


def record_label_family_signature(record: Any) -> str:
    existing = getattr(record, "label_family_signature", None)
    if existing:
        return str(existing)
    labels = [normalize_signal(label) for label in (getattr(record, "group_labels", []) or [])]
    return stable_id("label_family", sorted(labels))


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
