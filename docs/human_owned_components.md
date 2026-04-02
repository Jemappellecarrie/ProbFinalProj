# Human-Owned Components

This document tracks what is now implemented as a baseline versus what remains genuinely human-owned or unresolved.

## Implemented Baselines

### Feature Extraction

File: `backend/app/features/human_feature_strategy.py`

- `HumanCuratedFeatureExtractor.extract_features(words: list[WordEntry]) -> list[WordFeatures]`
- Status: implemented as a deterministic semantic baseline
- Current behavior:
  - canonicalizes word forms deterministically and surfaces canonical collisions in feature debug metadata
  - separates raw source facts from derived semantic/theme/tag signals
  - derives semantic tags, theme tags, lexical signals, and phonetic signals from seed metadata plus lightweight string heuristics
  - attaches a deterministic `semantic_sketch` vector plus explicit support/provenance metadata for downstream tracing
- Still human-owned:
  - semantic ontology design
  - external knowledge sourcing
  - confidence calibration and ambiguity-aware feature curation

### Semantic Group Proposal

File: `backend/app/generators/semantic.py`

- `HumanSemanticGroupGenerator.generate(entries, features_by_word_id, context) -> list[GroupCandidate]`
- Status: implemented as a real semantic baseline
- Current behavior:
  - proposes 4-word semantic groups from shared semantic and theme signals
  - ranks membership by semantic-sketch centroid similarity
  - deduplicates exact duplicate proposals, filters weak candidates, and exposes normalized rule signatures
  - records shared signals, member scores, centroid evidence, provenance, and local confidence in `metadata`
- Still human-owned:
  - broader semantic recall beyond current metadata-rich seeds
  - better category naming and polysemy handling
  - editorial judgment for what counts as a truly puzzle-worthy category

### Puzzle Composition

File: `backend/app/pipeline/builder.py`

- `HumanPuzzleComposer.compose(groups_by_type, context) -> list[PuzzleCandidate]`
- Status: implemented as a Stage 2 mixed-composer baseline
- Current behavior:
  - searches compatible 4-group combinations
  - enforces 16 unique words
  - records rejected overlaps and structured composition diagnostics in trace-friendly metadata
  - ranks boards using group confidence, cross-group centroid similarity, diversity bonuses, and mechanism-redundancy penalties
  - preserves current `PuzzleCandidate` contracts and debug metadata while letting the pipeline choose mixed semantic / lexical / theme boards when they outrank semantic-only fallbacks
- Still human-owned:
  - final fairness policy
  - richer cross-type mix design and editorial tuning
  - richer freshness, deception, and editor-facing compatibility rules

### Ambiguity / Leakage Evaluation

File: `backend/app/solver/human_ambiguity_strategy.py`

- `HumanAmbiguityEvaluator.evaluate(...) -> VerificationResult`
- Status: implemented as the Stage 1 quality-control ambiguity baseline
- Current behavior:
  - computes per-word assigned versus competing-group fit with leakage margins
  - computes cross-group pressure summaries and board-level pressure metrics
  - enumerates all 4-word board subsets to surface suspicious alternative groups with supporting evidence
  - emits structured `AmbiguityReport` evidence for verifier/scorer/debug consumers
- Still human-owned:
  - final ambiguity definition
  - editorial fairness calibration
  - threshold tuning beyond the current Stage 1 policy layer

### Internal Verification

File: `backend/app/solver/verifier.py`

- `InternalPuzzleVerifier.verify(puzzle, context) -> VerificationResult`
- Status: implemented as the Stage 1 verification baseline
- Current behavior:
  - applies structural checks, solver sanity checks, and Stage 1 ambiguity evidence
  - returns explicit `accept` / `borderline` / `reject` decisions
  - emits reject reasons, warning flags, summary metrics, and evidence references
- Still human-owned:
  - editorial rejection policy beyond Stage 1
  - solver weighting or calibration beyond the current deterministic baseline

### Final Scoring / Ranking

File: `backend/app/scoring/human_scoring_strategy.py`

- `HumanOwnedPuzzleScorer.score(puzzle, verification, context) -> PuzzleScore`
- Status: implemented as the Stage 1 ranking baseline
- Current behavior:
  - scores group coherence, board balance, evidence quality, ambiguity, leakage, and alternative-group pressure
  - produces an interpretable component breakdown plus deterministic ranking support
  - feeds batch evaluation and top-k ordering without claiming final editorial quality
- Still human-owned:
  - long-horizon score calibration
  - benchmarked editorial ranking policy beyond Stage 1

## Still Placeholder / Human-Owned

### Lexical Group Proposal

File: `backend/app/generators/lexical.py`

- `HumanLexicalGroupGenerator.generate(...) -> list[GroupCandidate]`
- Status: implemented as a high-precision lexical baseline
- Current behavior:
  - proposes 4-word lexical groups from explicit shared prefix and suffix rules
  - attaches normalized pattern signatures, per-word match evidence, centroid support, and generator provenance
  - deduplicates weaker duplicate pattern views and limits candidate volume to exact, deterministic matches
- Still human-owned:
  - broader lexical/template coverage beyond the current affix-focused baseline
  - editorial judgment for which orthographic gimmicks are puzzle-worthy

### Phonetic / Wordplay Proposal

File: `backend/app/generators/phonetic.py`

- `HumanPhoneticGroupGenerator.generate(...) -> list[GroupCandidate]`
- Status: implemented as a narrow Stage 3 phonetic baseline
- Current behavior:
  - proposes only high-precision 4-word phonetic groups from a local pronunciation inventory
  - supports perfect-rhyme groups and exact homophone classes when all four members have explicit local evidence
  - attaches normalized phonetic signatures, pronunciation membership evidence, rule signatures, and deterministic provenance
  - keeps candidate volume controlled by requiring exact 4-word support and deduplicating by word set
- Still human-owned:
  - broader phonetic coverage beyond the current inventory
  - decisions about which wordplay families deserve editorial preference or suppression
  - calibration of phonetic difficulty beyond the current Stage 3 local policy

### Theme / Trivia Proposal

File: `backend/app/generators/theme.py`

- `HumanThemeGroupGenerator.generate(...) -> list[GroupCandidate]`
- Status: implemented as a curated theme/trivia baseline
- Current behavior:
  - resolves a small curated theme inventory against the seed word set
  - emits 4-word theme groups with explicit pack ids, provenance, membership evidence, and centroid support
  - keeps the inventory compact and deterministic rather than treating theme generation as open-ended retrieval
- Still human-owned:
  - broader curated inventory management
  - editorial policy for how broad or niche trivia categories may become

### Style Analysis

File: `backend/app/scoring/style_analysis.py`

- `HumanStyleAnalyzer.analyze(puzzle, verification, context) -> StyleAnalysisReport`
- Status: implemented as an interpretable Stage 3 baseline
- Current behavior:
  - emits group-level mechanism, label-quality, evidence-interpretability, and novelty/redundancy signals
  - emits board-level mechanism-mix, balance, monotony, coherence-versus-trickiness, and style-alignment summaries
  - compares board metrics against local target bands from `data/reference/style_targets_v1.json`
  - exposes within-band / out-of-band comparisons and uses them additively in ranking and borderline-policy hooks
- Still human-owned:
  - target-band curation against richer historical references
  - final editorial interpretation of style drift and ranking
  - any claim that NYT-likeness or editorial quality is solved

## Recommended Next Order

1. benchmark curation and refinement of the local style target bands
2. broader lexical/theme/phonetic inventory expansion
3. calibration of ranking and verifier thresholds against larger historical fixture sets
4. editor-facing tooling for reviewing batch-calibration drift and false-positive warnings

## Stage 4 Note

Stage 4 release hardening does not change the ownership map above. It adds
tests, CI, docs, release-validation scripts, and frontend/debug wording so the
existing implemented baselines are easier to run, review, and submit without
overclaiming what remains human judgment.
