"""Semantic group generation strategies."""

from __future__ import annotations

from collections import defaultdict

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.features.semantic_baseline import (
    SEMANTIC_BASELINE_EXTRACTION_MODE,
    cosine_similarity,
    mean_pairwise_similarity,
    normalize_signal,
    signal_label,
    vector_centroid,
)
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate
from app.utils.ids import stable_id

MIN_SHARED_SIGNAL_SUPPORT = 4
MIN_SEMANTIC_CONFIDENCE = 0.35
NEAR_DUPLICATE_WORD_OVERLAP = 3


class MockSemanticGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline semantic generator for demo mode."""

    group_type = GroupType.SEMANTIC
    hint_key = "semantic"
    strategy_name = "mock_semantic_group_generator"


class HumanSemanticGroupGenerator(MockFeatureGroupedGenerator):
    """Generate semantic candidates from shared semantic/theme signals.

    The experimental branch used embedding clustering. This hand-port keeps the
    same local-cohesion idea, but makes the proposal step more interpretable by
    grounding it in shared extracted signals and similarity-ranked membership.
    """

    group_type = GroupType.SEMANTIC
    hint_key = "semantic"
    strategy_name = "human_semantic_group_generator"

    @staticmethod
    def _semantic_vector(feature: WordFeatures) -> list[float]:
        raw = feature.debug_attributes.get("semantic_sketch", [])
        return [float(value) for value in raw] if isinstance(raw, list) else []

    @staticmethod
    def _shared_signals(feature: WordFeatures) -> list[str]:
        return sorted(set(feature.semantic_tags + feature.theme_tags))

    @staticmethod
    def _signal_namespace(
        signal: str,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
    ) -> str:
        semantic_support = sum(
            1 for entry in entries if signal in features_by_word_id[entry.word_id].semantic_tags
        )
        theme_support = sum(
            1 for entry in entries if signal in features_by_word_id[entry.word_id].theme_tags
        )
        return "semantic" if semantic_support >= theme_support else "theme"

    @staticmethod
    def _candidate_sort_key(candidate: GroupCandidate) -> tuple[float, int, str, tuple[str, ...]]:
        signal_support = int(candidate.metadata.get("signal_support", 0))
        return (
            -candidate.confidence,
            -signal_support,
            candidate.metadata.get("normalized_label", normalize_signal(candidate.label)),
            tuple(candidate.words),
        )

    def _resolve_label(self, entries: list[WordEntry], signal: str) -> str:
        explicit_labels = sorted(
            {
                str(entry.metadata.get("seed_group_label", "")).strip()
                for entry in entries
                if entry.metadata.get("seed_group_label")
            }
        )
        if len(explicit_labels) == 1:
            return explicit_labels[0]

        hint_values = sorted(
            {
                (
                    entry.known_group_hints.get("semantic")
                    or entry.known_group_hints.get("theme")
                    or ""
                ).strip()
                for entry in entries
                if (entry.known_group_hints.get("semantic") or entry.known_group_hints.get("theme"))
            }
        )
        if len(hint_values) == 1:
            return signal_label(hint_values[0])

        return signal_label(signal)

    def _candidate_for_signal(
        self,
        signal: str,
        bucket_entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
    ) -> GroupCandidate | None:
        vectors_by_word_id = {
            entry.word_id: self._semantic_vector(features_by_word_id[entry.word_id])
            for entry in bucket_entries
        }
        centroid = vector_centroid(list(vectors_by_word_id.values()))
        ranked_entries = sorted(
            bucket_entries,
            key=lambda entry: (
                -cosine_similarity(vectors_by_word_id[entry.word_id], centroid),
                entry.surface_form,
            ),
        )
        selected_entries = ranked_entries[:4]
        selected_vectors = [vectors_by_word_id[entry.word_id] for entry in selected_entries]
        member_scores = [
            {
                "word": entry.surface_form,
                "word_id": entry.word_id,
                "centroid_similarity": round(
                    cosine_similarity(vectors_by_word_id[entry.word_id], centroid),
                    4,
                ),
            }
            for entry in selected_entries
        ]

        focus = min(1.0, 4.0 / len(bucket_entries))
        local_similarity = mean_pairwise_similarity(selected_vectors)
        confidence = round(max(0.0, min(1.0, (0.75 * local_similarity) + (0.25 * focus))), 4)
        if confidence < MIN_SEMANTIC_CONFIDENCE:
            return None

        shared_signals = sorted(
            set.intersection(
                *[
                    set(self._shared_signals(features_by_word_id[entry.word_id]))
                    for entry in selected_entries
                ]
            )
        )
        label = self._resolve_label(selected_entries, signal)
        normalized_label = normalize_signal(label)
        signal_namespace = self._signal_namespace(signal, selected_entries, features_by_word_id)
        rule_signature = f"{signal_namespace}:{signal}"
        rationale = (
            f"Baseline semantic candidate from shared signal '{signal}' with "
            f"mean pairwise similarity {local_similarity:.3f}."
        )
        word_ids = [entry.word_id for entry in selected_entries]
        words = [entry.surface_form for entry in selected_entries]

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
                "normalized_label": normalized_label,
                "rule_signature": rule_signature,
                "shared_tags": shared_signals or [signal],
                "selected_signal": signal,
                "semantic_centroid": [round(value, 6) for value in centroid],
                "mean_pairwise_similarity": round(local_similarity, 4),
                "signal_support": len(bucket_entries),
                "focus_ratio": round(focus, 4),
                "evidence": {
                    "shared_signals": shared_signals or [signal],
                    "member_scores": member_scores,
                    "support_size": len(bucket_entries),
                    "supporting_word_ids": sorted(entry.word_id for entry in bucket_entries),
                    "dropped_word_ids": sorted(entry.word_id for entry in ranked_entries[4:]),
                },
                "provenance": {
                    "generator": self.strategy_name,
                    "feature_mode": SEMANTIC_BASELINE_EXTRACTION_MODE,
                    "signal_namespace": signal_namespace,
                },
                "diagnostics": {
                    "duplicate_signals_merged": [],
                    "candidate_signature": stable_id(
                        "semantic_candidate",
                        rule_signature,
                        tuple(word_ids),
                    ),
                },
                "baseline_mode": "semantic_candidate_generation",
            },
        )

    def _merge_duplicate_signal(
        self,
        existing: GroupCandidate,
        candidate: GroupCandidate,
        signal: str,
    ) -> GroupCandidate:
        merged_signal = normalize_signal(signal)
        merged_shared = sorted(
            set(existing.metadata.get("shared_tags", []))
            | set(candidate.metadata.get("shared_tags", []))
        )
        merged_duplicates = sorted(
            set(existing.metadata["diagnostics"].get("duplicate_signals_merged", []))
            | {merged_signal}
        )
        merged_evidence_signals = sorted(
            set(existing.metadata["evidence"].get("shared_signals", []))
            | set(candidate.metadata["evidence"].get("shared_signals", []))
            | {merged_signal}
        )

        if candidate.confidence > existing.confidence:
            kept = candidate
        else:
            kept = existing

        kept.metadata["shared_tags"] = merged_shared
        kept.metadata["evidence"]["shared_signals"] = merged_evidence_signals
        kept.metadata["diagnostics"]["duplicate_signals_merged"] = [
            item
            for item in merged_duplicates
            if item != normalize_signal(kept.metadata.get("selected_signal", ""))
        ]
        return kept

    @staticmethod
    def _is_near_duplicate(left: GroupCandidate, right: GroupCandidate) -> bool:
        overlap = len(set(left.word_ids) & set(right.word_ids))
        return overlap >= NEAR_DUPLICATE_WORD_OVERLAP and left.metadata.get(
            "normalized_label"
        ) == right.metadata.get("normalized_label")

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        buckets: dict[str, list[WordEntry]] = defaultdict(list)
        entries_by_id = {entry.word_id: entry for entry in entries}

        for entry in entries:
            feature = features_by_word_id.get(entry.word_id)
            if feature is None:
                continue
            for signal in self._shared_signals(feature):
                buckets[signal].append(entry)

        deduped: dict[tuple[str, ...], GroupCandidate] = {}
        for signal, bucket_entries in sorted(buckets.items()):
            if len(bucket_entries) < MIN_SHARED_SIGNAL_SUPPORT:
                continue
            candidate = self._candidate_for_signal(signal, bucket_entries, features_by_word_id)
            if candidate is None:
                continue

            dedupe_key = tuple(sorted(candidate.word_ids))
            existing = deduped.get(dedupe_key)
            if existing is None:
                deduped[dedupe_key] = candidate
                continue
            deduped[dedupe_key] = self._merge_duplicate_signal(existing, candidate, signal)

        selected: list[GroupCandidate] = []
        for candidate in sorted(deduped.values(), key=self._candidate_sort_key):
            near_duplicate = next(
                (existing for existing in selected if self._is_near_duplicate(existing, candidate)),
                None,
            )
            if near_duplicate is not None:
                near_duplicate.metadata["diagnostics"].setdefault(
                    "near_duplicates_rejected",
                    [],
                ).append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "candidate_words": candidate.words,
                        "reason": "overlap_ge_3_same_normalized_label",
                    }
                )
                continue
            selected.append(candidate)

        context.run_metadata.setdefault("generator_diagnostics", {})[self.strategy_name] = {
            "candidate_count": len(selected),
            "signals_considered": sorted(buckets),
        }

        return sorted(
            selected,
            key=lambda candidate: (
                -candidate.confidence,
                -int(candidate.metadata.get("signal_support", 0)),
                candidate.metadata.get("normalized_label", normalize_signal(candidate.label)),
                tuple(entries_by_id[word_id].surface_form for word_id in candidate.word_ids),
            ),
        )
