"""Base classes and helpers for group generators."""

from __future__ import annotations

from abc import ABC
from collections import defaultdict

from app.core.enums import GroupType
from app.domain.protocols import GroupGenerator
from app.domain.value_objects import GenerationContext
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate
from app.utils.ids import new_id


class BaseGroupGenerator(GroupGenerator, ABC):
    """Common helper behavior for baseline generators."""

    group_type: GroupType
    strategy_name = "base_group_generator"

    def _build_candidate(
        self,
        bucket_key: str,
        entries: list[WordEntry],
        extraction_mode: str,
    ) -> GroupCandidate:
        first = entries[0]
        label = first.metadata.get("seed_group_label", bucket_key.replace("_", " ").title())
        rationale = first.metadata.get(
            "seed_group_rationale",
            f"Baseline demo {self.group_type.value} bucket derived from seed metadata.",
        )
        words = [entry.surface_form for entry in entries[:4]]
        word_ids = [entry.word_id for entry in entries[:4]]
        return GroupCandidate(
            candidate_id=new_id(f"group_{self.group_type.value}"),
            group_type=self.group_type,
            label=label,
            rationale=rationale,
            words=words,
            word_ids=word_ids,
            source_strategy=self.strategy_name,
            extraction_mode=extraction_mode,
            confidence=0.4,
            metadata={
                "baseline_only": True,
                "bucket_key": bucket_key,
            },
        )


class MockFeatureGroupedGenerator(BaseGroupGenerator):
    """Baseline generator that groups on explicit seed hints."""

    hint_key: str

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        buckets: dict[str, list[WordEntry]] = defaultdict(list)
        extraction_mode = "mock_demo"
        for entry in entries:
            hint = entry.known_group_hints.get(self.hint_key)
            if not hint:
                continue
            if entry.word_id not in features_by_word_id:
                continue
            buckets[hint].append(entry)

        candidates: list[GroupCandidate] = []
        for bucket_key, bucket_entries in sorted(buckets.items()):
            if len(bucket_entries) < 4:
                continue
            candidates.append(self._build_candidate(bucket_key, bucket_entries[:4], extraction_mode))
        return candidates
