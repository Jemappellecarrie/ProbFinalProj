"""Theme and trivia group generation strategies."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

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

THEME_SOURCE = "curated_theme_inventory_v1"
MAX_CURATED_THEME_PACKS_PER_REQUEST = 2


@dataclass(frozen=True, slots=True)
class ThemePack:
    """Small curated inventory entry used by the Stage 2 theme generator."""

    theme_name: str
    label: str
    rationale: str
    source: str
    members: tuple[str, str, str, str]
    shared_signals: tuple[str, ...]
    base_confidence: float


CURATED_THEME_PACKS: tuple[ThemePack, ...] = (
    ThemePack(
        theme_name="pac_man_ghosts",
        label="Pac-Man ghosts",
        rationale="Curated theme group from the canonical Pac-Man ghost roster.",
        source=THEME_SOURCE,
        members=("blinky", "clyde", "inky", "pinky"),
        shared_signals=("ghost", "pacman"),
        base_confidence=0.88,
    ),
    ThemePack(
        theme_name="teenage_mutant_ninja_turtles",
        label="Teenage Mutant Ninja Turtles",
        rationale="Curated theme group from the four named Ninja Turtles.",
        source=THEME_SOURCE,
        members=("donatello", "leonardo", "michelangelo", "raphael"),
        shared_signals=("fictional_character", "tmnt"),
        base_confidence=0.88,
    ),
    ThemePack(
        theme_name="classical_planets",
        label="Planets",
        rationale="Curated theme group from the classical inner-planet set in the seed inventory.",
        source=THEME_SOURCE,
        members=("earth", "mars", "mercury", "venus"),
        shared_signals=("astronomy", "planet"),
        base_confidence=0.84,
    ),
    ThemePack(
        theme_name="common_gemstones",
        label="Gemstones",
        rationale="Curated theme group from four common gemstone names in the seed inventory.",
        source=THEME_SOURCE,
        members=("jade", "opal", "ruby", "topaz"),
        shared_signals=("gemstone", "mineral"),
        base_confidence=0.84,
    ),
)


class MockThemeGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline theme generator for demo mode."""

    group_type = GroupType.THEME
    hint_key = "theme"
    strategy_name = "mock_theme_group_generator"


class HumanThemeGroupGenerator(MockFeatureGroupedGenerator):
    """Generate theme candidates from an explicit curated inventory."""

    group_type = GroupType.THEME
    hint_key = "theme"
    strategy_name = "human_theme_group_generator"

    @staticmethod
    def _semantic_vector(feature: WordFeatures) -> list[float]:
        raw = feature.debug_attributes.get("semantic_sketch", [])
        return [float(value) for value in raw] if isinstance(raw, list) else []

    @staticmethod
    def _candidate_sort_key(candidate: GroupCandidate) -> tuple[float, str, tuple[str, ...]]:
        return (
            -candidate.confidence,
            candidate.metadata.get("theme_name", normalize_signal(candidate.label)),
            tuple(candidate.words),
        )

    def _candidate_for_pack(
        self,
        pack: ThemePack,
        entries_by_normalized: dict[str, WordEntry],
        features_by_word_id: dict[str, WordFeatures],
    ) -> GroupCandidate | None:
        if any(member not in entries_by_normalized for member in pack.members):
            return None

        selected_entries = [entries_by_normalized[member] for member in pack.members]
        vectors = [
            self._semantic_vector(features_by_word_id[entry.word_id]) for entry in selected_entries
        ]
        centroid = vector_centroid(vectors)
        mean_similarity = mean_pairwise_similarity(vectors)
        confidence = round(clamp_unit(pack.base_confidence + (0.08 * mean_similarity)), 4)
        word_ids = [entry.word_id for entry in selected_entries]
        words = [entry.surface_form for entry in selected_entries]
        rule_signature = f"{self.group_type.value}:{pack.theme_name}"

        return GroupCandidate(
            candidate_id=stable_id(
                f"group_{self.group_type.value}",
                rule_signature,
                tuple(word_ids),
            ),
            group_type=self.group_type,
            label=pack.label,
            rationale=pack.rationale,
            words=words,
            word_ids=word_ids,
            source_strategy=self.strategy_name,
            extraction_mode=SEMANTIC_BASELINE_EXTRACTION_MODE,
            confidence=confidence,
            metadata={
                "normalized_label": normalize_signal(pack.label),
                "theme_name": pack.theme_name,
                "theme_source": pack.source,
                "rule_signature": rule_signature,
                "shared_tags": list(pack.shared_signals),
                "semantic_centroid": [round(value, 6) for value in centroid],
                "mean_pairwise_similarity": round(mean_similarity, 4),
                "evidence": {
                    "theme_name": pack.theme_name,
                    "theme_label": pack.label,
                    "source": pack.source,
                    "shared_signals": list(pack.shared_signals),
                    "membership": [
                        {
                            "word": entry.surface_form,
                            "word_id": entry.word_id,
                            "normalized_word": features_by_word_id[entry.word_id].normalized,
                            "member_key": member,
                            "source": pack.source,
                        }
                        for member, entry in zip(pack.members, selected_entries, strict=True)
                    ],
                },
                "provenance": {
                    "generator": self.strategy_name,
                    "feature_mode": SEMANTIC_BASELINE_EXTRACTION_MODE,
                    "theme_source": pack.source,
                },
                "diagnostics": {
                    "candidate_signature": stable_id(
                        "theme_candidate",
                        rule_signature,
                        tuple(word_ids),
                    ),
                },
                "baseline_mode": "theme_candidate_generation",
            },
        )

    @staticmethod
    def _active_packs(context: GenerationContext) -> tuple[ThemePack, ...]:
        if (
            not bool(context.run_metadata.get("limit_curated_theme_packs"))
            or context.seed is None
            or len(CURATED_THEME_PACKS) <= MAX_CURATED_THEME_PACKS_PER_REQUEST
        ):
            return CURATED_THEME_PACKS

        indexed_packs = list(enumerate(CURATED_THEME_PACKS))
        rng = Random(context.seed)
        rng.shuffle(indexed_packs)
        chosen = sorted(
            indexed_packs[:MAX_CURATED_THEME_PACKS_PER_REQUEST],
            key=lambda item: item[0],
        )
        return tuple(pack for _, pack in chosen)

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        entries_by_normalized = {
            features_by_word_id[entry.word_id].normalized: entry
            for entry in sorted(entries, key=lambda item: (item.surface_form, item.word_id))
            if entry.word_id in features_by_word_id
        }
        active_packs = self._active_packs(context)

        deduped: dict[tuple[str, ...], GroupCandidate] = {}
        for pack in active_packs:
            candidate = self._candidate_for_pack(pack, entries_by_normalized, features_by_word_id)
            if candidate is None:
                continue
            key = tuple(sorted(candidate.word_ids))
            current = deduped.get(key)
            if current is None or candidate.confidence > current.confidence:
                deduped[key] = candidate

        selected = sorted(deduped.values(), key=self._candidate_sort_key)
        context.run_metadata.setdefault("generator_diagnostics", {})[self.strategy_name] = {
            "candidate_count": len(selected),
            "packs_considered": [pack.theme_name for pack in active_packs],
            "packs_available": [pack.theme_name for pack in CURATED_THEME_PACKS],
            "packs_matched": [candidate.metadata["theme_name"] for candidate in selected],
        }
        return selected
