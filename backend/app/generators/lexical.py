"""Lexical/pattern group generation strategies."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import ClassVar

from app.core.enums import GroupType
from app.core.stage1_quality import clamp_unit
from app.domain.value_objects import GenerationContext
from app.features.semantic_baseline import (
    SEMANTIC_BASELINE_EXTRACTION_MODE,
    mean_pairwise_similarity,
    normalize_signal,
    vector_centroid,
)
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate
from app.utils.ids import stable_id

MIN_PATTERN_SUPPORT = 4
MAX_PATTERN_SUPPORT = 4
MIN_PATTERN_LENGTH = 2
MAX_PATTERN_LENGTH = 3
MIN_LEXICAL_CONFIDENCE = 0.72
NEAR_DUPLICATE_WORD_OVERLAP = 3


@dataclass(frozen=True, slots=True)
class LexicalPattern:
    """Explicit lexical rule extracted from normalized words."""

    pattern_type: str
    normalized_pattern: str
    signal_key: str
    matched_feature: str
    position: str

    @property
    def pattern_length(self) -> int:
        return len(self.normalized_pattern)


class MockLexicalGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline lexical generator for demo mode."""

    group_type = GroupType.LEXICAL
    hint_key = "lexical"
    strategy_name = "mock_lexical_group_generator"


class HumanLexicalGroupGenerator(MockFeatureGroupedGenerator):
    """Generate high-precision lexical groups from explicit pattern rules."""

    group_type = GroupType.LEXICAL
    hint_key = "lexical"
    strategy_name = "human_lexical_group_generator"
    _pattern_priority: ClassVar[dict[str, int]] = {
        "shared_suffix": 0,
        "shared_prefix": 1,
        "shared_substring": 2,
        "double_letter": 3,
    }

    @staticmethod
    def _semantic_vector(feature: WordFeatures) -> list[float]:
        raw = feature.debug_attributes.get("semantic_sketch", [])
        return [float(value) for value in raw] if isinstance(raw, list) else []

    @staticmethod
    def _patterns_for_word(normalized_word: str) -> list[LexicalPattern]:
        patterns: list[LexicalPattern] = []
        for length in range(MIN_PATTERN_LENGTH, min(MAX_PATTERN_LENGTH, len(normalized_word)) + 1):
            prefix = normalized_word[:length]
            suffix = normalized_word[-length:]
            patterns.append(
                LexicalPattern(
                    pattern_type="shared_prefix",
                    normalized_pattern=prefix,
                    signal_key=f"prefix_{prefix}",
                    matched_feature=f"prefix:{prefix}",
                    position="prefix",
                )
            )
            patterns.append(
                LexicalPattern(
                    pattern_type="shared_suffix",
                    normalized_pattern=suffix,
                    signal_key=f"suffix_{suffix}",
                    matched_feature=f"suffix:{suffix}",
                    position="suffix",
                )
            )
        return patterns

    @classmethod
    def _pattern_sort_key(cls, pattern: LexicalPattern) -> tuple[int, int, str]:
        return (
            cls._pattern_priority.get(pattern.pattern_type, 99),
            -pattern.pattern_length,
            pattern.normalized_pattern,
        )

    @classmethod
    def _candidate_sort_key(
        cls, candidate: GroupCandidate
    ) -> tuple[float, int, int, str, tuple[str, ...]]:
        return (
            -candidate.confidence,
            -int(candidate.metadata.get("pattern_length", 0)),
            cls._pattern_priority.get(candidate.metadata.get("pattern_type", ""), 99),
            candidate.metadata.get("normalized_label", normalize_signal(candidate.label)),
            tuple(candidate.words),
        )

    @staticmethod
    def _label_for_pattern(pattern: LexicalPattern) -> str:
        rendered = pattern.normalized_pattern.upper()
        if pattern.pattern_type == "shared_prefix":
            return f"Starts with {rendered}"
        if pattern.pattern_type == "shared_suffix":
            return f"Ends with -{rendered}"
        if pattern.pattern_type == "shared_substring":
            return f'Contains "{rendered}"'
        return "Contains doubled letter"

    @staticmethod
    def _rationale_for_pattern(pattern: LexicalPattern, mean_similarity: float) -> str:
        if pattern.pattern_type == "shared_prefix":
            return (
                f"Lexical candidate from the shared prefix '{pattern.normalized_pattern}' "
                f"with mean pairwise similarity {mean_similarity:.3f}."
            )
        if pattern.pattern_type == "shared_suffix":
            return (
                f"Lexical candidate from the shared suffix '{pattern.normalized_pattern}' "
                f"with mean pairwise similarity {mean_similarity:.3f}."
            )
        if pattern.pattern_type == "shared_substring":
            return (
                f"Lexical candidate from the shared substring '{pattern.normalized_pattern}' "
                f"with mean pairwise similarity {mean_similarity:.3f}."
            )
        return (
            "Lexical candidate from an explicit repeated-letter pattern with "
            f"mean pairwise similarity {mean_similarity:.3f}."
        )

    @staticmethod
    def _confidence_for_pattern(
        pattern: LexicalPattern,
        bucket_size: int,
        mean_similarity: float,
    ) -> float:
        support_bonus = 0.1 if bucket_size == 4 else 0.0
        length_bonus = 0.1 if pattern.pattern_length >= 3 else 0.05
        return round(
            clamp_unit(0.5 + support_bonus + length_bonus + (0.25 * mean_similarity)),
            4,
        )

    @staticmethod
    def _is_near_duplicate(left: GroupCandidate, right: GroupCandidate) -> bool:
        overlap = len(set(left.word_ids) & set(right.word_ids))
        return overlap >= NEAR_DUPLICATE_WORD_OVERLAP and (
            left.metadata.get("pattern_type") == right.metadata.get("pattern_type")
        )

    def _candidate_for_pattern(
        self,
        pattern: LexicalPattern,
        bucket_entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
    ) -> GroupCandidate | None:
        if not MIN_PATTERN_SUPPORT <= len(bucket_entries) <= MAX_PATTERN_SUPPORT:
            return None

        ordered_entries = sorted(
            bucket_entries,
            key=lambda entry: (
                features_by_word_id[entry.word_id].normalized,
                entry.surface_form,
                entry.word_id,
            ),
        )
        vectors = [
            self._semantic_vector(features_by_word_id[entry.word_id]) for entry in ordered_entries
        ]
        centroid = vector_centroid(vectors)
        mean_similarity = mean_pairwise_similarity(vectors)
        confidence = self._confidence_for_pattern(pattern, len(ordered_entries), mean_similarity)
        if confidence < MIN_LEXICAL_CONFIDENCE:
            return None

        word_ids = [entry.word_id for entry in ordered_entries]
        words = [entry.surface_form for entry in ordered_entries]
        label = self._label_for_pattern(pattern)
        rationale = self._rationale_for_pattern(pattern, mean_similarity)
        rule_signature = (
            f"{self.group_type.value}:{pattern.pattern_type}:{pattern.normalized_pattern}"
        )

        return GroupCandidate(
            candidate_id=stable_id(
                f"group_{self.group_type.value}",
                rule_signature,
                tuple(word_ids),
            ),
            group_type=self.group_type,
            label=label,
            rationale=rationale,
            words=words,
            word_ids=word_ids,
            source_strategy=self.strategy_name,
            extraction_mode=SEMANTIC_BASELINE_EXTRACTION_MODE,
            confidence=confidence,
            metadata={
                "normalized_label": normalize_signal(label),
                "pattern_type": pattern.pattern_type,
                "normalized_pattern": pattern.normalized_pattern,
                "pattern_length": pattern.pattern_length,
                "rule_signature": rule_signature,
                "shared_tags": [pattern.signal_key],
                "semantic_centroid": [round(value, 6) for value in centroid],
                "mean_pairwise_similarity": round(mean_similarity, 4),
                "signal_support": len(ordered_entries),
                "evidence": {
                    "pattern_type": pattern.pattern_type,
                    "normalized_pattern": pattern.normalized_pattern,
                    "matched_feature": pattern.matched_feature,
                    "shared_signals": [pattern.signal_key],
                    "support_size": len(ordered_entries),
                    "word_matches": [
                        {
                            "word": entry.surface_form,
                            "word_id": entry.word_id,
                            "normalized_word": features_by_word_id[entry.word_id].normalized,
                            "match_position": pattern.position,
                            "matched_text": pattern.normalized_pattern.upper(),
                        }
                        for entry in ordered_entries
                    ],
                },
                "provenance": {
                    "generator": self.strategy_name,
                    "feature_mode": SEMANTIC_BASELINE_EXTRACTION_MODE,
                    "pattern_source": "normalized_word_rules",
                },
                "diagnostics": {
                    "candidate_signature": stable_id(
                        "lexical_candidate",
                        rule_signature,
                        tuple(word_ids),
                    ),
                },
                "baseline_mode": "lexical_candidate_generation",
            },
        )

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        pattern_buckets: dict[LexicalPattern, list[WordEntry]] = defaultdict(list)
        for entry in entries:
            feature = features_by_word_id.get(entry.word_id)
            if feature is None or not feature.normalized:
                continue
            for pattern in self._patterns_for_word(feature.normalized):
                pattern_buckets[pattern].append(entry)

        deduped_by_words: dict[tuple[str, ...], GroupCandidate] = {}
        for pattern in sorted(pattern_buckets, key=self._pattern_sort_key):
            candidate = self._candidate_for_pattern(
                pattern,
                pattern_buckets[pattern],
                features_by_word_id,
            )
            if candidate is None:
                continue
            word_key = tuple(sorted(candidate.word_ids))
            current = deduped_by_words.get(word_key)
            if current is None:
                deduped_by_words[word_key] = candidate
                continue
            replace = (
                int(candidate.metadata.get("pattern_length", 0)),
                candidate.confidence,
                candidate.metadata.get("pattern_type", ""),
            ) > (
                int(current.metadata.get("pattern_length", 0)),
                current.confidence,
                current.metadata.get("pattern_type", ""),
            )
            if replace:
                deduped_by_words[word_key] = candidate

        selected: list[GroupCandidate] = []
        rejected_near_duplicates: list[dict[str, object]] = []
        for candidate in sorted(deduped_by_words.values(), key=self._candidate_sort_key):
            near_duplicate = next(
                (existing for existing in selected if self._is_near_duplicate(existing, candidate)),
                None,
            )
            if near_duplicate is not None:
                rejected_near_duplicates.append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "candidate_words": candidate.words,
                        "reason": "overlap_ge_3_same_pattern_family",
                    }
                )
                continue
            selected.append(candidate)

        context.run_metadata.setdefault("generator_diagnostics", {})[self.strategy_name] = {
            "candidate_count": len(selected),
            "patterns_considered": [
                {
                    "pattern_type": pattern.pattern_type,
                    "normalized_pattern": pattern.normalized_pattern,
                    "support_size": len(pattern_buckets[pattern]),
                }
                for pattern in sorted(pattern_buckets, key=self._pattern_sort_key)
                if MIN_PATTERN_SUPPORT <= len(pattern_buckets[pattern]) <= MAX_PATTERN_SUPPORT
            ],
            "rejected_near_duplicates": rejected_near_duplicates,
        }
        return sorted(selected, key=self._candidate_sort_key)
