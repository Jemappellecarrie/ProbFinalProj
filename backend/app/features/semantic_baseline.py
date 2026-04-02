"""Reusable helpers for the semantic baseline pipeline.

These helpers intentionally provide a deterministic, inspectable approximation
of semantic evidence. They are not meant to represent final editorial truth,
but they make it possible to hand-port the branch's embedding-oriented ideas
without introducing hidden runtime model downloads.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from statistics import mean

from app.schemas.feature_models import (
    CanonicalFormEvidence,
    RawSemanticSourceFacts,
    SemanticSupportSummary,
    WordEntry,
)

SEMANTIC_BASELINE_EXTRACTION_MODE = "semantic_baseline_v1"
SEMANTIC_BASELINE_FEATURE_VERSION = "1.1.0"
SEMANTIC_SKETCH_DIMENSIONS = 32

_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
_SPLIT_PATTERN = re.compile(r"[_\-\s]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(slots=True)
class SemanticEvidenceBundle:
    """Structured semantic evidence derived from a single word entry."""

    semantic_tags: list[str]
    lexical_signals: list[str]
    phonetic_signals: list[str]
    theme_tags: list[str]
    label_hints: list[str]
    semantic_tokens: list[str]
    semantic_sketch: list[float]
    canonical_form: CanonicalFormEvidence
    raw_source_facts: RawSemanticSourceFacts
    support: SemanticSupportSummary
    provenance: list[str]
    notes: list[str]


def _clean_text(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.strip())


def _coerce_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(str(item)) for item in value if _clean_text(str(item))]


def _sorted_unique(values: list[str]) -> list[str]:
    normalized = {normalize_signal(value) for value in values if normalize_signal(value)}
    return sorted(normalized)


def normalize_signal(value: str) -> str:
    """Return a normalized token suitable for semantic evidence."""

    cleaned = _clean_text(value).lower()
    if not cleaned:
        return ""
    collapsed = _NON_ALNUM_PATTERN.sub("_", cleaned)
    return collapsed.strip("_")


def signal_label(value: str) -> str:
    """Convert a normalized signal into a human-readable label."""

    token = normalize_signal(value)
    if not token:
        return ""
    parts = [part for part in _SPLIT_PATTERN.split(token) if part]
    rendered_parts: list[str] = []
    for part in parts:
        if len(part) <= 4 and part.isalpha():
            rendered_parts.append(part.upper())
        else:
            rendered_parts.append(part.capitalize())
    return " ".join(rendered_parts)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for two dense vectors."""

    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def vector_centroid(vectors: list[list[float]]) -> list[float]:
    """Return the normalized centroid of a collection of vectors."""

    if not vectors:
        return [0.0] * SEMANTIC_SKETCH_DIMENSIONS

    width = len(vectors[0])
    centroid = [0.0] * width
    for vector in vectors:
        for index, value in enumerate(vector):
            centroid[index] += value

    scale = float(len(vectors))
    averaged = [value / scale for value in centroid]
    norm = math.sqrt(sum(value * value for value in averaged))
    if norm == 0.0:
        return averaged
    return [value / norm for value in averaged]


def mean_pairwise_similarity(vectors: list[list[float]]) -> float:
    """Return the mean pairwise cosine similarity for a vector set."""

    if len(vectors) < 2:
        return 0.0

    similarities = [
        cosine_similarity(vectors[left_index], vectors[right_index])
        for left_index in range(len(vectors))
        for right_index in range(left_index + 1, len(vectors))
    ]
    return mean(similarities) if similarities else 0.0


def canonical_form_for_entry(
    entry: WordEntry,
    colliding_word_ids: list[str] | None = None,
) -> CanonicalFormEvidence:
    """Return canonicalization metadata for one seed entry."""

    normalized_source = _clean_text(entry.normalized or entry.surface_form)
    canonical_normalized = (
        normalize_signal(normalized_source or entry.surface_form) or entry.word_id
    )
    tokenized_words = [part for part in canonical_normalized.split("_") if part]
    collisions = sorted(colliding_word_ids or [entry.word_id])
    return CanonicalFormEvidence(
        original_surface=entry.surface_form,
        display_form=_clean_text(entry.surface_form),
        normalized_source=normalized_source,
        canonical_normalized=canonical_normalized,
        tokenized_words=tokenized_words,
        collision_count=len(collisions),
        colliding_word_ids=collisions,
    )


def raw_source_facts_for_entry(entry: WordEntry) -> RawSemanticSourceFacts:
    """Preserve raw metadata facts before baseline derivation."""

    return RawSemanticSourceFacts(
        semantic_metadata=_coerce_string_list(entry.metadata.get("semantic_tags")),
        theme_metadata=_coerce_string_list(entry.metadata.get("theme_tags")),
        lexical_metadata=_coerce_string_list(entry.metadata.get("lexical_signals")),
        phonetic_metadata=_coerce_string_list(entry.metadata.get("phonetic_signals")),
        group_hints={
            key: _clean_text(value)
            for key, value in sorted(entry.known_group_hints.items())
            if _clean_text(value)
        },
        label_hint_sources=sorted(
            {
                _clean_text(str(entry.metadata["seed_group_label"]))
                for key in ("seed_group_label",)
                if entry.metadata.get(key)
            }
        ),
    )


def support_summary_for_entry(
    semantic_tags: list[str],
    theme_tags: list[str],
    label_hints: list[str],
) -> SemanticSupportSummary:
    """Classify how much semantic support exists for one word."""

    notes: list[str] = []
    if semantic_tags or theme_tags:
        support_level = "metadata_backed"
    elif label_hints:
        support_level = "hint_only"
        notes.append("Semantic neighborhood is backed only by normalized label hints.")
    else:
        support_level = "surface_only"
        notes.append(
            "No semantic metadata or group hints were available; "
            "sketch falls back to surface features."
        )

    return SemanticSupportSummary(
        semantic_signal_count=len(semantic_tags),
        theme_signal_count=len(theme_tags),
        label_hint_count=len(label_hints),
        support_level=support_level,
        notes=notes,
    )


def sketch_for_entry(
    semantic_tags: list[str],
    theme_tags: list[str],
    label_hints: list[str],
    normalized_word: str,
) -> list[float]:
    """Build a deterministic semantic sketch vector from weighted tokens."""

    weighted_tokens: list[tuple[str, float]] = []
    weighted_tokens.extend((f"semantic:{tag}", 1.0) for tag in semantic_tags)
    weighted_tokens.extend((f"theme:{tag}", 0.95) for tag in theme_tags)
    weighted_tokens.extend((f"label:{hint}", 0.65) for hint in label_hints)
    weighted_tokens.append((f"surface:{normalized_word}", 0.35))

    trigrams = [
        normalized_word[index : index + 3]
        for index in range(max(0, len(normalized_word) - 2))
        if len(normalized_word[index : index + 3]) == 3
    ]
    if not trigrams:
        trigrams = [normalized_word]
    weighted_tokens.extend((f"gram:{trigram}", 0.15) for trigram in trigrams)

    vector = [0.0] * SEMANTIC_SKETCH_DIMENSIONS
    for token, weight in weighted_tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % SEMANTIC_SKETCH_DIMENSIONS
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[index] += weight * sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [round(value / norm, 6) for value in vector]


def build_lexical_signals(word: str) -> list[str]:
    """Return deterministic lexical signals for a normalized word."""

    signals = [f"length:{len(word)}"]
    if len(word) >= 2:
        signals.append(f"prefix:{word[:2]}")
        signals.append(f"suffix:{word[-2:]}")
    if len(word) >= 3:
        signals.append(f"prefix:{word[:3]}")
        signals.append(f"suffix:{word[-3:]}")

    vowel_pattern = "".join("V" if character in "aeiou" else "C" for character in word)
    signals.append(f"shape:{vowel_pattern}")
    return _sorted_unique(signals)


def build_phonetic_signals(word: str) -> list[str]:
    """Return lightweight phonetic-style signals for a normalized word."""

    signals = [f"rhyme:{word[-3:]}" if len(word) >= 3 else f"rhyme:{word}"]
    vowel_count = sum(1 for character in word if character in "aeiou")
    signals.append(f"vowel_count:{vowel_count}")
    if len(word) >= 2:
        signals.append(f"onset:{word[:2]}")
    for index in range(len(word) - 1):
        if word[index] == word[index + 1]:
            signals.append(f"double:{word[index]}")
            break
    return _sorted_unique(signals)


def build_semantic_evidence(
    entry: WordEntry,
    colliding_word_ids: list[str] | None = None,
) -> SemanticEvidenceBundle:
    """Return a deterministic semantic evidence bundle for one word entry."""

    canonical_form = canonical_form_for_entry(entry, colliding_word_ids=colliding_word_ids)
    raw_source_facts = raw_source_facts_for_entry(entry)

    semantic_tags = _sorted_unique(
        raw_source_facts.semantic_metadata
        + (
            [raw_source_facts.group_hints["semantic"]]
            if raw_source_facts.group_hints.get("semantic")
            else []
        )
    )
    theme_tags = _sorted_unique(
        raw_source_facts.theme_metadata
        + (
            [raw_source_facts.group_hints["theme"]]
            if raw_source_facts.group_hints.get("theme")
            else []
        )
    )
    label_hints = _sorted_unique(
        raw_source_facts.label_hint_sources + list(raw_source_facts.group_hints.values())
    )
    semantic_tokens = sorted(set(semantic_tags + theme_tags))
    support = support_summary_for_entry(semantic_tags, theme_tags, label_hints)
    lexical_signals = build_lexical_signals(canonical_form.canonical_normalized)
    phonetic_signals = build_phonetic_signals(canonical_form.canonical_normalized)
    semantic_sketch = sketch_for_entry(
        semantic_tags=semantic_tags,
        theme_tags=theme_tags,
        label_hints=label_hints,
        normalized_word=canonical_form.canonical_normalized,
    )

    provenance = [
        "normalized_seed_fields",
        "seed_metadata",
        "known_group_hints",
        "deterministic_semantic_sketch",
        "string_heuristics",
    ]
    notes = list(support.notes)
    if canonical_form.collision_count > 1:
        notes.append("Canonical normalized form collides with another seed entry.")

    return SemanticEvidenceBundle(
        semantic_tags=semantic_tags,
        lexical_signals=lexical_signals,
        phonetic_signals=phonetic_signals,
        theme_tags=theme_tags,
        label_hints=label_hints,
        semantic_tokens=semantic_tokens,
        semantic_sketch=semantic_sketch,
        canonical_form=canonical_form,
        raw_source_facts=raw_source_facts,
        support=support,
        provenance=provenance,
        notes=notes,
    )
