"""Semantic group generation strategies.

File location:
    backend/app/generators/semantic.py

This module contains:
    - A baseline demo generator that groups words using explicit seed hints.
    - A human-owned generator using KMeans clustering on sentence embeddings.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from sklearn.cluster import KMeans

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate
from app.utils.ids import new_id


class MockSemanticGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline semantic generator for demo mode."""

    group_type = GroupType.SEMANTIC
    hint_key = "semantic"
    strategy_name = "mock_semantic_group_generator"


class HumanSemanticGroupGenerator(MockFeatureGroupedGenerator):
    """KMeans-based semantic grouping using sentence-transformer embeddings.

    Clusters words by their embedding similarity, then selects the four words
    closest to each cluster centroid. Confidence is the mean pairwise cosine
    similarity among the four selected words.
    """

    group_type = GroupType.SEMANTIC
    hint_key = "semantic"
    strategy_name = "human_semantic_group_generator"

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        valid_entries = [
            e
            for e in entries
            if e.word_id in features_by_word_id
            and "embedding" in features_by_word_id[e.word_id].debug_attributes
        ]

        if len(valid_entries) < 4:
            return []

        vecs = np.array(
            [
                features_by_word_id[e.word_id].debug_attributes["embedding"]
                for e in valid_entries
            ],
            dtype=np.float32,
        )

        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs_norm = vecs / np.maximum(norms, 1e-9)

        n_clusters = max(2, len(valid_entries) // 4)
        kmeans = KMeans(n_clusters=n_clusters, random_state=context.seed or 42, n_init=10)
        labels = kmeans.fit_predict(vecs_norm)

        candidates: list[GroupCandidate] = []
        for cluster_idx in range(n_clusters):
            cluster_indices = [i for i, lbl in enumerate(labels) if lbl == cluster_idx]
            if len(cluster_indices) < 4:
                continue

            cluster_entries = [valid_entries[i] for i in cluster_indices]
            cluster_vecs = vecs_norm[cluster_indices]
            centroid = kmeans.cluster_centers_[cluster_idx]

            sims_to_centroid = cluster_vecs @ centroid
            top_local = np.argsort(sims_to_centroid)[::-1][:4]

            top_entries = [cluster_entries[j] for j in top_local]
            top_vecs = cluster_vecs[top_local]

            pairwise_sims = [
                float(top_vecs[pi] @ top_vecs[pj])
                for pi in range(4)
                for pj in range(pi + 1, 4)
            ]
            confidence = max(0.0, min(1.0, float(np.mean(pairwise_sims))))

            all_tags: list[str] = []
            for e in top_entries:
                all_tags.extend(features_by_word_id[e.word_id].semantic_tags)

            if all_tags:
                label = Counter(all_tags).most_common(1)[0][0].title()
            else:
                label = f"Semantic Group {cluster_idx + 1}"

            candidates.append(
                GroupCandidate(
                    candidate_id=new_id(f"group_{self.group_type.value}"),
                    group_type=self.group_type,
                    label=label,
                    rationale=(
                        f"KMeans cluster {cluster_idx} with mean pairwise cosine similarity "
                        f"{confidence:.3f}."
                    ),
                    words=[e.surface_form for e in top_entries],
                    word_ids=[e.word_id for e in top_entries],
                    source_strategy=self.strategy_name,
                    extraction_mode="human_curated_v1",
                    confidence=confidence,
                    metadata={
                        "cluster_idx": cluster_idx,
                        "cluster_size": len(cluster_entries),
                    },
                )
            )

        return candidates
