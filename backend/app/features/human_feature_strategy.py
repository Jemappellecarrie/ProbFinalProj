"""Semantic baseline feature extraction.

This module now contains a real, deterministic baseline implementation for the
first roadmap step: semantic-oriented feature extraction. It intentionally does
not claim to be the final editorial feature ontology. The remaining ontology,
curation, and calibration work stays human-owned.
"""

from __future__ import annotations

from collections import defaultdict

from app.features.base import BaseWordFeatureExtractor
from app.features.semantic_baseline import (
    SEMANTIC_BASELINE_EXTRACTION_MODE,
    SEMANTIC_BASELINE_FEATURE_VERSION,
    build_semantic_evidence,
)
from app.schemas.feature_models import WordEntry, WordFeatures


class HumanCuratedFeatureExtractor(BaseWordFeatureExtractor):
    """Deterministic semantic baseline extractor.

    The teammate branch used sentence-embedding features directly. This hand-port
    preserves the core idea of attaching reusable semantic evidence to every
    word, but does so with an inspectable semantic-sketch baseline that keeps
    runtime setup simple and deterministic for tests and debug workflows.
    """

    extractor_name = "human_curated_feature_extractor"

    def extract_features(self, words: list[WordEntry]) -> list[WordFeatures]:
        """Return baseline semantic feature records for the provided words."""

        collision_map: dict[str, list[str]] = defaultdict(list)
        for entry in words:
            normalized_key = build_semantic_evidence(entry).canonical_form.canonical_normalized
            collision_map[normalized_key].append(entry.word_id)

        records: list[WordFeatures] = []
        for entry in words:
            canonical_key = build_semantic_evidence(entry).canonical_form.canonical_normalized
            evidence = build_semantic_evidence(
                entry,
                colliding_word_ids=collision_map[canonical_key],
            )
            records.append(
                WordFeatures(
                    word_id=entry.word_id,
                    normalized=evidence.canonical_form.canonical_normalized,
                    semantic_tags=evidence.semantic_tags,
                    lexical_signals=evidence.lexical_signals,
                    phonetic_signals=evidence.phonetic_signals,
                    theme_tags=evidence.theme_tags,
                    extraction_mode=SEMANTIC_BASELINE_EXTRACTION_MODE,
                    feature_version=SEMANTIC_BASELINE_FEATURE_VERSION,
                    provenance=evidence.provenance,
                    debug_attributes={
                        "canonical_form": evidence.canonical_form.model_dump(mode="json"),
                        "raw_source_facts": evidence.raw_source_facts.model_dump(mode="json"),
                        "support": evidence.support.model_dump(mode="json"),
                        "semantic_sketch": evidence.semantic_sketch,
                        "semantic_evidence": {
                            "semantic_tokens": evidence.semantic_tokens,
                            "label_hints": evidence.label_hints,
                            "notes": evidence.notes,
                        },
                        "baseline_mode": "semantic_feature_extraction",
                    },
                )
            )
        return records
