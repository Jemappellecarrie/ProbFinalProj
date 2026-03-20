# CLAUDE.md — Project Implementation Log

This file documents all changes made by Claude Code to the `ProbFinalProj` repository.
It is intended to give future sessions full context about what has been implemented and why.

---

## Project Overview

**NYT Connections Puzzle Generator** — Duke 2026 Spring Probability/ML final project.

The repo provides a FastAPI + React scaffold where all "human-owned" core logic was
initially `NotImplementedError` stubs. The goal was to implement the MVP pipeline
(TODO 1 & 2): Sentence Transformers embedding + cosine-similarity clustering to replace
all mock implementations and produce a working end-to-end generation pipeline.

**Backend root:** `backend/`
**Entry point:** `backend/app/main.py`
**Pipeline orchestration:** `backend/app/pipeline/orchestration.py`

---

## Git History Summary

All changes follow the **feature branch → merge to main** workflow (never commit directly
to main). Six feature branches were created, implemented, and merged:

```
main
├── feature/add-ml-dependencies       (merged)
├── feature/feature-extraction        (merged)
├── feature/semantic-generator        (merged)
├── feature/puzzle-composer           (merged)
├── feature/quality-control          (merged)
└── feature/human-pipeline-factory   (merged)
```

---

## What Was Changed, File by File

### 1. `backend/pyproject.toml`
**Branch:** `feature/add-ml-dependencies`

Added four ML dependencies to `[project] dependencies`:
```toml
"sentence-transformers>=3.0.0,<4.0.0",
"scikit-learn>=1.5.0,<2.0.0",
"numpy>=1.26.0,<3.0.0",
"nltk>=3.9.0,<4.0.0",
```

After pulling, run:
```bash
cd backend && pip install -e .
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

---

### 2. `backend/app/features/human_feature_strategy.py`
**Branch:** `feature/feature-extraction`

**Was:** `NotImplementedError` stub.

**Now:** Full implementation of `HumanCuratedFeatureExtractor`:
- `__init__(model_name="all-MiniLM-L6-v2")` — loads `SentenceTransformer` (lazy import)
- `extract_features(words)` — batch-encodes all words, returns `list[WordFeatures]`
  - **semantic_tags**: WordNet synset hypernyms (top 3 synsets × top 2 hypernyms) +
    `entry.known_group_hints.get("semantic")`
  - **lexical_signals**: `prefix:XX`, `prefix:XXX`, `suffix:XX`, `suffix:XXX`, `length:N`
  - **phonetic_signals**: `rhyme:XXX` (last 3 chars), `syllables:N` (vowel count),
    `double:X` (first double-letter detected)
  - **theme_tags**: `entry.known_group_hints.get("theme")` + `entry.metadata["theme_tags"]`
  - **debug_attributes**: `{"embedding": vec.tolist(), "model_name": ...}` — the 384-dim
    embedding stored here so downstream components can reuse it without re-encoding

---

### 3. `backend/app/pipeline/orchestration.py`
**Branch:** `feature/feature-extraction`

**Change:** Added one line after feature extraction in `PuzzleGenerationPipeline.run()`:
```python
context.run_metadata["features_by_word_id"] = features_by_word_id
```
This makes the word embeddings available to the ambiguity evaluator and verifier
via `context.run_metadata`, without changing any interface signatures.

---

### 4. `backend/app/generators/semantic.py`
**Branch:** `feature/semantic-generator`

**Was:** `HumanSemanticGroupGenerator.generate()` raised `NotImplementedError`.
`MockSemanticGroupGenerator` was left unchanged.

**Now:** `HumanSemanticGroupGenerator.generate()` implements KMeans clustering:
1. Filter entries to those with `"embedding"` in `debug_attributes`
2. Build L2-normalized embedding matrix `vecs_norm` (float32)
3. `KMeans(n_clusters=max(2, n_words//4), random_state=seed or 42, n_init=10)`
4. For each cluster with ≥ 4 members:
   - Pick the 4 words with highest cosine similarity to the cluster centroid
   - `confidence` = mean pairwise cosine similarity of those 4 words ∈ [0, 1]
   - `label` = most frequent `semantic_tag` among the 4 words (Title Case)
5. Returns `list[GroupCandidate]` (may be empty if no cluster has ≥ 4 members)

Top-level imports added: `numpy`, `sklearn.cluster.KMeans`, `collections.Counter`,
`app.utils.ids.new_id`.

---

### 5. `backend/app/pipeline/builder.py`
**Branch:** `feature/puzzle-composer`

**Was:** `HumanPuzzleComposer.compose()` raised `NotImplementedError`.
`BaselinePuzzleComposer` was left unchanged.

**Now:**
1. Delegate to `BaselinePuzzleComposer().compose(...)` to get structurally valid
   candidates (16 unique words, Cartesian product of groups)
2. Re-rank by `sum(g.confidence for g in puzzle.groups)` descending
3. Return top-5 candidates

---

### 6. `backend/app/solver/human_ambiguity_strategy.py`
**Branch:** `feature/quality-control`

**Was:** `HumanAmbiguityEvaluator.evaluate()` raised `NotImplementedError`.

**Now:** Embedding-based cross-group leakage detection:
- Recover embeddings from `context.run_metadata["features_by_word_id"]`
- Compute cosine similarity for every pair of words in different groups
- Record `WordGroupLeakage` for pairs where `sim > LEAKAGE_THRESHOLD = 0.65`
- `leakage_estimate = min(1.0, len(leakage_records) * 0.1 + max_cross_sim * 0.3)`
- `ambiguity_score = min(1.0, 0.4 * leakage_estimate + 0.6 * alternative_count * 0.2)`
  where `alternative_count = solver_result.alternative_groupings_detected`
- Risk levels: `CRITICAL` if score ≥ 0.7, `HIGH` if ≥ 0.45, `MEDIUM` if > 0, `LOW` else
- Returns `VerificationResult` (same interface as baseline evaluator)

---

### 7. `backend/app/solver/verifier.py`
**Branch:** `feature/quality-control`

**Was:** `InternalPuzzleVerifier.verify()` raised `NotImplementedError`.

**Now:** `InternalPuzzleVerifier` gets `__init__` and `verify`:
- `__init__(solver, solver_ensemble, ambiguity_evaluator)` — defaults to
  `HumanAmbiguityEvaluator()` (lazy import to avoid circular deps)
- `verify(puzzle, context)`:
  1. Delegates to `BaselinePuzzleVerifier` for structural checks (16 unique words)
     and ambiguity evaluation via the injected evaluator
  2. Adds **group-type diversity check**: rejects if < 2 distinct `GroupType` values
  3. Adds **minimum confidence check**: rejects if any group has `confidence < 0.2`
  4. Returns merged `VerificationResult`

---

### 8. `backend/app/scoring/human_scoring_strategy.py`
**Branch:** `feature/quality-control`

**Was:** `HumanOwnedPuzzleScorer.score()` raised `NotImplementedError`.

**Now:** Three-component scoring formula:
```
coherence      = mean(g.confidence for g in puzzle.groups)
ambiguity_pen  = verification.ambiguity_score
human_likeness = 0.5 * (distinct_group_types / 4) + 0.5 * min(1, avg_word_len / 8)
overall        = max(0, 0.5*coherence + 0.3*human_likeness - 0.2*ambiguity_pen)
```
Uses `BaselineStyleAnalyzer` for `style_analysis` field (HumanStyleAnalyzer is A+, not MVP).

---

### 9. `backend/app/pipeline/human_pipeline.py` *(new file)*
**Branch:** `feature/human-pipeline-factory`

Factory function `build_human_pipeline(word_repository)` wiring:
- `HumanCuratedFeatureExtractor()`
- `[HumanSemanticGroupGenerator(), MockLexicalGroupGenerator(),
   MockPhoneticGroupGenerator(), MockThemeGroupGenerator()]`
- `HumanPuzzleComposer()`
- `InternalPuzzleVerifier(solver, solver_ensemble, HumanAmbiguityEvaluator())`
- `HumanOwnedPuzzleScorer(style_analyzer=BaselineStyleAnalyzer())`

Note: Lexical, Phonetic, and Theme generators remain as Mock variants (A+ scope).

---

### 10. `backend/app/services/generation_service.py`
**Branch:** `feature/human-pipeline-factory`

**Was:** Hard-coded `build_demo_pipeline()`; raised `RuntimeError` when `demo_mode=False`.

**Now:** Selects pipeline at init time based on `settings.demo_mode`:
```python
if settings.demo_mode:
    self._pipeline = build_demo_pipeline(self._word_repository)
else:
    from app.pipeline.human_pipeline import build_human_pipeline
    self._pipeline = build_human_pipeline(self._word_repository)
```
`generate_puzzle()` also sets `mode=GenerationMode.HUMAN_MIXED` when not in demo mode.

---

### 11. `backend/tests/test_human_owned_placeholders.py`
**Branch:** `feature/human-pipeline-factory`

**Was:** Three tests asserting `NotImplementedError` (valid for stubs).

**Now:** Updated to test real implementations:
- `test_human_feature_extractor_is_implemented` — checks 384-dim embedding present
- `test_human_feature_extractor_returns_lexical_signals` — checks prefix/suffix/length signals
- `test_human_semantic_generator_is_implemented` — runs generator on 8 words, checks output shape
- `test_human_scorer_is_implemented` — checks scorer name attribute

---

## Embedding Data Flow

```
HumanCuratedFeatureExtractor.extract_features()
  └── SentenceTransformer.encode() → (N, 384) float32
  └── stored: WordFeatures.debug_attributes["embedding"] = vec.tolist()
                    ↓
  orchestration.py injects → context.run_metadata["features_by_word_id"]
                    ↓
HumanSemanticGroupGenerator.generate()
  └── KMeans on L2-normalized embeddings
  └── GroupCandidate.confidence = mean pairwise cosine sim
                    ↓
HumanPuzzleComposer.compose()
  └── rank by sum(group.confidence)
                    ↓
HumanAmbiguityEvaluator.evaluate()
  └── cross-group cosine sim → leakage_estimate, ambiguity_score
                    ↓
HumanOwnedPuzzleScorer.score()
  └── overall = 0.5*coherence + 0.3*human_likeness - 0.2*ambiguity_pen
```

---

## How to Run

### Demo mode (original, mock components):
```bash
cd backend
CONNECTIONS_DEMO_MODE=true uvicorn app.main:app --reload
```

### Human mode (ML pipeline, real embeddings):
```bash
cd backend
CONNECTIONS_DEMO_MODE=false uvicorn app.main:app --reload
```

### Run tests:
```bash
cd backend && python -m pytest tests/ -v
```

### Quick integration check (human mode):
```bash
cd backend
CONNECTIONS_DEMO_MODE=false python -c "
from app.config.settings import get_settings
from app.pipeline.human_pipeline import build_human_pipeline
from app.repositories.word_repository import FileBackedWordRepository
from app.core.enums import GenerationMode
from app.domain.value_objects import GenerationContext

settings = get_settings()
repo = FileBackedWordRepository(settings)
pipeline = build_human_pipeline(repo)
ctx = GenerationContext(
    request_id='test',
    mode=GenerationMode.HUMAN_MIXED,
    demo_mode=False,
    include_trace=False,
    developer_mode=True,
    seed=42,
)
result = pipeline.run(ctx)
print('groups:', [g.label for g in result.puzzle.groups])
print('passed:', result.verification.passed)
print('overall:', result.score.overall)
"
```

### API validation:
```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"include_trace": true, "developer_mode": true}'
# Check: selected_components.feature_extractor == "human_curated_feature_extractor"
```

---

## What Is NOT Implemented (A+ scope, out of MVP)

- `generators/lexical.py` — `HumanLexicalGroupGenerator`
- `generators/phonetic.py` — `HumanPhoneticGroupGenerator`
- `generators/theme.py` — `HumanThemeGroupGenerator`
- `scoring/style_analysis.py` — `HumanStyleAnalyzer`

These still use their `Mock*` / `Baseline*` counterparts.
