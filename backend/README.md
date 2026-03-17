# Backend

FastAPI backend for the Connections puzzle generator scaffold.

## Responsibilities

- Load and normalize seed word data.
- Extract or load word features.
- Run group generators through a shared orchestration pipeline.
- Compose, verify, score, and expose puzzle candidates.
- Preserve trace metadata for debugging and future offline evaluation.

## Demo Mode

Demo mode wires the pipeline with baseline implementations:

- `MockWordFeatureExtractor`
- `MockSemanticGroupGenerator`
- `MockLexicalGroupGenerator`
- `MockPhoneticGroupGenerator`
- `MockThemeGroupGenerator`
- `BaselinePuzzleComposer`
- `MockSolverBackend`
- `BaselinePuzzleVerifier`
- `MockPuzzleScorer`

These components are intentionally transparent and simple. They exist so the repository can run end-to-end without claiming to solve the project-defining quality problem.
