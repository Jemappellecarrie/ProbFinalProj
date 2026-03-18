# Human-Owned Components

This document is the implementation map for the logic intentionally left unimplemented or baseline-only.

## Feature Extraction

File: `backend/app/features/human_feature_strategy.py`

- `HumanCuratedFeatureExtractor.extract_features(words: list[WordEntry]) -> list[WordFeatures]`
- Responsibility: high-quality semantic, phonetic, lexical, and theme feature engineering.
- Success looks like: stable, versioned features with enough metadata for generation and offline evaluation.

## Semantic Group Proposal

File: `backend/app/generators/semantic.py`

- `HumanSemanticGroupGenerator.generate(entries, features_by_word_id, context) -> list[GroupCandidate]`
- Responsibility: propose human-coherent semantic categories rather than seed-hint buckets.
- Success looks like: strong category quality, interpretable labels, and useful generator metadata.

## Lexical Group Proposal

File: `backend/app/generators/lexical.py`

- `HumanLexicalGroupGenerator.generate(...) -> list[GroupCandidate]`
- Responsibility: identify pattern groups worth using in a puzzle, not just any shared prefix/suffix.
- Success looks like: puzzle-worthy patterns with low accidental overlap.

## Phonetic / Wordplay Proposal

File: `backend/app/generators/phonetic.py`

- `HumanPhoneticGroupGenerator.generate(...) -> list[GroupCandidate]`
- Responsibility: propose fair, recognizable wordplay groups.
- Success looks like: sound-based groupings that are playful without becoming arbitrary.

## Theme / Trivia Proposal

File: `backend/app/generators/theme.py`

- `HumanThemeGroupGenerator.generate(...) -> list[GroupCandidate]`
- Responsibility: turn curated knowledge into usable puzzle groups.
- Success looks like: strong theme groups with clear provenance and bounded trivia depth.

## Puzzle Composition

File: `backend/app/pipeline/builder.py`

- `HumanPuzzleComposer.compose(groups_by_type, context) -> list[PuzzleCandidate]`
- Responsibility: combine group candidates while reasoning about compatibility, leakage, and fairness.
- Success looks like: only plausible puzzle boards make it forward to verification/ranking.

## Ambiguity / Leakage Evaluation

File: `backend/app/solver/human_ambiguity_strategy.py`

- `HumanAmbiguityEvaluator.evaluate(puzzle, solver_result, context, ensemble_result=None) -> VerificationResult`
- Responsibility: estimate cross-group ambiguity, alternative regroupings, and leakage.
- Success looks like: fair puzzles pass, misleading puzzles fail, and the diagnostics are interpretable.

## Internal Verification

File: `backend/app/solver/verifier.py`

- `InternalPuzzleVerifier.verify(puzzle, context) -> VerificationResult`
- Responsibility: centralize final structural and fairness checks.
- Success looks like: a consistent pass/reject decision with actionable rejection reasons.

## Final Scoring / Ranking

File: `backend/app/scoring/human_scoring_strategy.py`

- `HumanOwnedPuzzleScorer.score(puzzle, verification, context) -> PuzzleScore`
- Responsibility: coherence, ambiguity, human-likeness, and overall ranking.
- Success looks like: rankings align with human judgment and remain debuggable.

## Style Analysis

File: `backend/app/scoring/style_analysis.py`

- `HumanStyleAnalyzer.analyze(puzzle, verification, context) -> StyleAnalysisReport`
- Responsibility: define the real style signals, archetypes, and NYT-likeness judgment.
- Success looks like: style metadata aligns with expert editorial judgment rather than placeholder structural cues.

## Recommended Implementation Order

1. Feature extraction
2. Semantic and lexical generators
3. Puzzle composition
4. Ambiguity evaluation and verification
5. Style analysis
6. Final scoring
7. Theme and phonetic depth improvements
