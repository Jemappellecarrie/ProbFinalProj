"""High-precision phonetic and wordplay group generation."""

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

PHONETIC_REFERENCE = "local_pronunciation_inventory_v1"
REQUIRED_BUCKET_SIZE = 4
MIN_PHONETIC_CONFIDENCE = 0.84


@dataclass(frozen=True, slots=True)
class PhoneticEntry:
    """Local pronunciation record used by the Stage 3 phonetic generator."""

    pronunciations: tuple[str, ...]
    rhyme_key: str
    spelling_rhyme_hint: str

    @property
    def exact_homophone_key(self) -> str:
        return self.pronunciations[0]

    @property
    def normalized_rhyme_key(self) -> str:
        return normalize_signal(self.rhyme_key)


LOCAL_PHONETIC_LEXICON: dict[str, PhoneticEntry] = {
    "bake": PhoneticEntry(("B EY1 K",), "EY1 K", "AKE"),
    "cake": PhoneticEntry(("K EY1 K",), "EY1 K", "AKE"),
    "lake": PhoneticEntry(("L EY1 K",), "EY1 K", "AKE"),
    "rake": PhoneticEntry(("R EY1 K",), "EY1 K", "AKE"),
    "heel": PhoneticEntry(("HH IY1 L",), "IY1 L", "EEL"),
    "keel": PhoneticEntry(("K IY1 L",), "IY1 L", "EEL"),
    "peel": PhoneticEntry(("P IY1 L",), "IY1 L", "EEL"),
    "reel": PhoneticEntry(("R IY1 L",), "IY1 L", "EEL"),
    "bash": PhoneticEntry(("B AE1 SH",), "AE1 SH", "ASH"),
    "cash": PhoneticEntry(("K AE1 SH",), "AE1 SH", "ASH"),
    "dash": PhoneticEntry(("D AE1 SH",), "AE1 SH", "ASH"),
    "mash": PhoneticEntry(("M AE1 SH",), "AE1 SH", "ASH"),
    "right": PhoneticEntry(("R AY1 T",), "AY1 T", "IGHT"),
    "write": PhoneticEntry(("R AY1 T",), "AY1 T", "IGHT"),
    "rite": PhoneticEntry(("R AY1 T",), "AY1 T", "IGHT"),
    "wright": PhoneticEntry(("R AY1 T",), "AY1 T", "IGHT"),
}


class MockPhoneticGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline phonetic generator for demo mode."""

    group_type = GroupType.PHONETIC
    hint_key = "phonetic"
    strategy_name = "mock_phonetic_group_generator"


class HumanPhoneticGroupGenerator(MockFeatureGroupedGenerator):
    """Generate a small number of evidence-rich phonetic wordplay candidates."""

    group_type = GroupType.PHONETIC
    hint_key = "phonetic"
    strategy_name = "human_phonetic_group_generator"
    _mechanism_priority: ClassVar[dict[str, int]] = {
        "exact_homophone": 0,
        "perfect_rhyme": 1,
    }

    @staticmethod
    def _semantic_vector(feature: WordFeatures) -> list[float]:
        raw = feature.debug_attributes.get("semantic_sketch", [])
        return [float(value) for value in raw] if isinstance(raw, list) else []

    @classmethod
    def _candidate_sort_key(
        cls, candidate: GroupCandidate
    ) -> tuple[int, float, str, tuple[str, ...]]:
        return (
            cls._mechanism_priority.get(candidate.metadata.get("phonetic_pattern_type", ""), 99),
            -candidate.confidence,
            candidate.metadata.get("normalized_phonetic_signature", ""),
            tuple(candidate.words),
        )

    @staticmethod
    def _confidence(mechanism: str, bucket_size: int) -> float:
        base = 0.92 if mechanism == "exact_homophone" else 0.86
        support_bonus = 0.04 if bucket_size == REQUIRED_BUCKET_SIZE else 0.0
        return round(clamp_unit(base + support_bonus), 4)

    @staticmethod
    def _label_for_bucket(mechanism: str, spelling_hint: str, words: list[str]) -> str:
        if mechanism == "exact_homophone":
            return f'Homophones of "{sorted(words)[0]}"'
        return f"Rhymes with -{spelling_hint}"

    @staticmethod
    def _rationale_for_bucket(mechanism: str, rhyme_key: str) -> str:
        if mechanism == "exact_homophone":
            return (
                "Phonetic candidate from an exact homophone class with matching local "
                f"pronunciation '{rhyme_key}'."
            )
        return (
            "Phonetic candidate from a perfect-rhyme family with shared stressed ending "
            f"'{rhyme_key}'."
        )

    def _candidate_for_bucket(
        self,
        *,
        mechanism: str,
        bucket_entries: list[WordEntry],
        bucket_key: str,
        spelling_hint: str,
        features_by_word_id: dict[str, WordFeatures],
    ) -> GroupCandidate | None:
        if len(bucket_entries) != REQUIRED_BUCKET_SIZE:
            return None

        ordered_entries = sorted(
            bucket_entries,
            key=lambda entry: (
                features_by_word_id[entry.word_id].normalized,
                entry.surface_form,
                entry.word_id,
            ),
        )
        word_ids = [entry.word_id for entry in ordered_entries]
        words = [entry.surface_form for entry in ordered_entries]
        vectors = [self._semantic_vector(features_by_word_id[word_id]) for word_id in word_ids]
        confidence = self._confidence(mechanism, len(ordered_entries))
        if confidence < MIN_PHONETIC_CONFIDENCE:
            return None

        label = self._label_for_bucket(mechanism, spelling_hint, words)
        normalized_signature = f"{mechanism}:{normalize_signal(bucket_key)}"
        rule_signature = f"phonetic:{normalized_signature}"
        shared_signals = [f"rhyme:{spelling_hint.lower()}"]

        pronunciation_membership = [
            {
                "word": entry.surface_form,
                "word_id": entry.word_id,
                "normalized_word": features_by_word_id[entry.word_id].normalized,
                "pronunciations": list(
                    LOCAL_PHONETIC_LEXICON[
                        features_by_word_id[entry.word_id].normalized
                    ].pronunciations
                ),
                "rhyme_key": LOCAL_PHONETIC_LEXICON[
                    features_by_word_id[entry.word_id].normalized
                ].rhyme_key,
                "spelling_rhyme_hint": spelling_hint,
            }
            for entry in ordered_entries
        ]

        evidence = {
            "phonetic_pattern_type": mechanism,
            "normalized_phonetic_signature": normalized_signature,
            "shared_signals": shared_signals,
            "pronunciation_membership": pronunciation_membership,
        }
        if mechanism == "exact_homophone":
            evidence["homophone_class"] = bucket_key
        else:
            evidence["rhyme_key"] = bucket_key

        return GroupCandidate(
            candidate_id=stable_id(
                f"group_{self.group_type.value}",
                rule_signature,
                tuple(word_ids),
            ),
            group_type=self.group_type,
            label=label,
            rationale=self._rationale_for_bucket(mechanism, bucket_key),
            words=words,
            word_ids=word_ids,
            source_strategy=self.strategy_name,
            extraction_mode=SEMANTIC_BASELINE_EXTRACTION_MODE,
            confidence=confidence,
            metadata={
                "normalized_label": normalize_signal(label),
                "generator_type": self.group_type.value,
                "phonetic_pattern_type": mechanism,
                "normalized_phonetic_signature": normalized_signature,
                "rule_signature": rule_signature,
                "shared_tags": shared_signals,
                "semantic_centroid": [round(value, 6) for value in vector_centroid(vectors)],
                "mean_pairwise_similarity": round(mean_pairwise_similarity(vectors), 4),
                "signal_support": len(ordered_entries),
                "evidence": evidence,
                "provenance": {
                    "generator": self.strategy_name,
                    "feature_mode": SEMANTIC_BASELINE_EXTRACTION_MODE,
                    "phonetic_reference": PHONETIC_REFERENCE,
                },
                "diagnostics": {
                    "candidate_signature": stable_id(
                        "phonetic_candidate",
                        rule_signature,
                        tuple(word_ids),
                    ),
                },
                "baseline_mode": "phonetic_candidate_generation",
            },
        )

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        supported_entries: list[tuple[WordEntry, PhoneticEntry]] = []
        for entry in entries:
            feature = features_by_word_id.get(entry.word_id)
            if feature is None:
                continue
            phonetic_entry = LOCAL_PHONETIC_LEXICON.get(feature.normalized)
            if phonetic_entry is None:
                continue
            supported_entries.append((entry, phonetic_entry))

        rhyme_buckets: dict[str, list[WordEntry]] = defaultdict(list)
        homophone_buckets: dict[str, list[WordEntry]] = defaultdict(list)
        rhyme_hints: dict[str, str] = {}
        for entry, phonetic_entry in supported_entries:
            rhyme_buckets[phonetic_entry.rhyme_key].append(entry)
            homophone_buckets[phonetic_entry.exact_homophone_key].append(entry)
            rhyme_hints[phonetic_entry.rhyme_key] = phonetic_entry.spelling_rhyme_hint
            rhyme_hints[phonetic_entry.exact_homophone_key] = phonetic_entry.spelling_rhyme_hint

        deduped_by_words: dict[tuple[str, ...], GroupCandidate] = {}
        for mechanism, buckets in (
            ("exact_homophone", homophone_buckets),
            ("perfect_rhyme", rhyme_buckets),
        ):
            for bucket_key, bucket_entries in sorted(buckets.items()):
                candidate = self._candidate_for_bucket(
                    mechanism=mechanism,
                    bucket_entries=bucket_entries,
                    bucket_key=bucket_key,
                    spelling_hint=rhyme_hints[bucket_key],
                    features_by_word_id=features_by_word_id,
                )
                if candidate is None:
                    continue
                word_key = tuple(sorted(candidate.word_ids))
                current = deduped_by_words.get(word_key)
                if current is None or self._candidate_sort_key(
                    candidate
                ) < self._candidate_sort_key(current):
                    deduped_by_words[word_key] = candidate

        selected = sorted(deduped_by_words.values(), key=self._candidate_sort_key)
        context.run_metadata.setdefault("generator_diagnostics", {})[self.strategy_name] = {
            "candidate_count": len(selected),
            "reference": PHONETIC_REFERENCE,
            "supported_words": sorted(
                features_by_word_id[entry.word_id].normalized for entry, _ in supported_entries
            ),
        }
        return selected
