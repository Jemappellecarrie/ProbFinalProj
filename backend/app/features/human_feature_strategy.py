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
"""

from __future__ import annotations

from app.features.base import BaseWordFeatureExtractor
from app.schemas.feature_models import WordEntry, WordFeatures


class HumanCuratedFeatureExtractor(BaseWordFeatureExtractor):
    """Sentence-Transformer + WordNet feature extractor."""

    extractor_name = "human_curated_feature_extractor"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._model_name = model_name

    def extract_features(self, words: list[WordEntry]) -> list[WordFeatures]:
        """Return curated feature records for the provided words."""

        if not words:
            return []

        normalized_words = [entry.normalized for entry in words]
        embeddings = self._model.encode(normalized_words, show_progress_bar=False)

        results: list[WordFeatures] = []
        for i, entry in enumerate(words):
            vec = embeddings[i]

            semantic_tags = self._get_semantic_tags(entry)
            lexical_signals = self._get_lexical_signals(entry.normalized)
            phonetic_signals = self._get_phonetic_signals(entry.normalized)
            theme_tags = self._get_theme_tags(entry)

            results.append(
                WordFeatures(
                    word_id=entry.word_id,
                    normalized=entry.normalized,
                    semantic_tags=sorted(set(semantic_tags)),
                    lexical_signals=sorted(set(lexical_signals)),
                    phonetic_signals=sorted(set(phonetic_signals)),
                    theme_tags=sorted(set(theme_tags)),
                    extraction_mode="human_curated_v1",
                    feature_version="1.0.0",
                    provenance=["wordnet", "sentence_transformers", "seed_hints"],
                    debug_attributes={
                        "embedding": vec.tolist(),
                        "model_name": self._model_name,
                    },
                )
            )

        return results

    def _get_semantic_tags(self, entry: WordEntry) -> list[str]:
        tags: list[str] = []

        if entry.known_group_hints.get("semantic"):
            tags.append(entry.known_group_hints["semantic"])

        try:
            from nltk.corpus import wordnet as wn

            synsets = wn.synsets(entry.normalized)
            for syn in synsets[:3]:
                for hypernym in syn.hypernyms()[:2]:
                    lemma_name = hypernym.lemmas()[0].name().replace("_", " ")
                    tags.append(lemma_name)
        except Exception:
            pass

        return tags

    def _get_lexical_signals(self, word: str) -> list[str]:
        signals: list[str] = []
        if len(word) >= 2:
            signals.append(f"prefix:{self._prefix(word, 2)}")
        if len(word) >= 3:
            signals.append(f"prefix:{self._prefix(word, 3)}")
        if len(word) >= 2:
            signals.append(f"suffix:{self._suffix(word, 2)}")
        if len(word) >= 3:
            signals.append(f"suffix:{self._suffix(word, 3)}")
        signals.append(f"length:{len(word)}")
        return signals

    def _get_phonetic_signals(self, word: str) -> list[str]:
        signals: list[str] = []
        if len(word) >= 3:
            signals.append(f"rhyme:{self._rhyme_signature(word, 3)}")
        vowels = sum(1 for c in word if c in "aeiou")
        signals.append(f"syllables:{max(1, vowels)}")
        for j in range(len(word) - 1):
            if word[j] == word[j + 1]:
                signals.append(f"double:{word[j]}")
                break
        return signals

    def _get_theme_tags(self, entry: WordEntry) -> list[str]:
        tags: list[str] = []
        if entry.known_group_hints.get("theme"):
            tags.append(entry.known_group_hints["theme"])
        tags.extend(entry.metadata.get("theme_tags", []))
        return tags
