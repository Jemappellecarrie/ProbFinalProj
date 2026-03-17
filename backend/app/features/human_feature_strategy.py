"""Human-owned feature extraction strategy.

File location:
    backend/app/features/human_feature_strategy.py

Purpose:
    Define the project-defining feature extraction layer for semantic tagging,
    phonetic/wordplay signals, lexical pattern mining, and theme/trivia curation.

Inputs:
    - `list[WordEntry]` containing normalized seed entries and source metadata.

Outputs:
    - `list[WordFeatures]` containing high-quality semantic, lexical, phonetic,
      and theme-oriented features suitable for generator and verifier use.

Pipeline role:
    This strategy sits immediately after seed loading and before every generator.

Why this is intentionally unimplemented:
    The quality of semantic tagging, theme curation, and phonetic/wordplay
    features is one of the primary differentiators of the final system. This
    logic should remain human-owned rather than silently approximated.

TODO[HUMAN_CORE]:
    Implement the real feature extraction strategy with rigorous canonicalization,
    provenance tracking, and feature confidence signals.

TODO[HUMAN_RESEARCH]:
    Determine the semantic tagging ontology, phonetic representation strategy,
    and theme knowledge sourcing plan.

TODO[HUMAN_HEURISTIC]:
    Add high-signal lexical and wordplay feature engineering that supports both
    generation and ambiguity detection without overfitting to seed artifacts.

TODO[HUMAN_DATA_CURATION]:
    Curate external or internal resources for theme/trivia coverage and define
    maintenance rules for updating them.

Acceptance criteria:
    - Produces stable, versioned feature records for every supported word entry.
    - Supports semantic, lexical, phonetic, and theme/trivia feature families.
    - Captures enough metadata for offline evaluation and ablation studies.
    - Improves generator precision without disguising uncertainty.
"""

from __future__ import annotations

from app.features.base import BaseWordFeatureExtractor
from app.schemas.feature_models import WordEntry, WordFeatures


class HumanCuratedFeatureExtractor(BaseWordFeatureExtractor):
    """Placeholder for the final human-owned feature extraction implementation."""

    extractor_name = "human_curated_feature_extractor"

    def extract_features(self, words: list[WordEntry]) -> list[WordFeatures]:
        """Return curated feature records for the provided words.

        Expected inputs:
            - Normalized `WordEntry` records with source metadata.

        Expected outputs:
            - One `WordFeatures` record per input word.

        Implementation notes:
            - Preserve versioning and provenance for each feature family.
            - Support multiple feature sources when research evolves.
            - Avoid hiding uncertainty; explicit confidence signals are preferred.

        Acceptance criteria:
            - Semantic tagging handles polysemy and grouping intent cleanly.
            - Phonetic features support rhyme/pun/homophone style generators.
            - Theme signals are curated enough for trivia-style group generation.
        """

        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement the human-owned feature extraction strategy."
        )
