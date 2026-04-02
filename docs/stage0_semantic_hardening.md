# Stage 0 Semantic Hardening

## Scope

Stage 0 hardens the existing semantic baseline so the repository can generate
real, semantic-heavy puzzles through the current FastAPI service flow with
deterministic-enough behavior for tests, batch evaluation, and downstream debug
inspection.

This pass is intentionally limited to:

- deterministic semantic feature extraction and canonicalization
- explainable semantic 4-word group candidate generation
- semantic-heavy puzzle composition with structured diagnostics
- service/evaluation compatibility and trace preservation
- regression tests and honest documentation updates

This pass intentionally does not claim to solve ambiguity policy, editorial
verification, final scoring, lexical/theme/phonetic generators, or historical
style calibration.

## Files Touched

Planned Stage 0 touch points:

- `backend/app/features/human_feature_strategy.py`
- `backend/app/features/semantic_baseline.py`
- `backend/app/generators/semantic.py`
- `backend/app/pipeline/builder.py`
- `backend/app/pipeline/orchestration.py`
- `backend/app/pipeline/trace.py`
- `backend/app/services/generation_service.py`
- `backend/app/schemas/feature_models.py`
- `backend/app/schemas/puzzle_models.py`
- `backend/app/utils/ids.py`
- `backend/tests/test_semantic_baseline.py`
- `backend/tests/test_pipeline.py`
- `backend/tests/test_evaluation_service.py`
- `backend/tests/test_schemas.py`
- `README.md`
- `docs/architecture.md`
- `docs/human_owned_components.md`

## Invariants Enforced

Stage 0 hardening is enforcing these contracts:

- `WordFeatures` remain explicit `WordFeatures` records with deterministic
  semantic evidence, canonicalized normalized forms, provenance, and sparse
  support represented honestly.
- semantic `GroupCandidate` outputs always contain exactly 4 unique words and 4
  unique word ids, a non-empty label/rationale, bounded confidence, and a
  traceable evidence bundle.
- semantic candidate ordering and tie-breaking are deterministic for fixed
  input/configuration.
- `PuzzleCandidate` outputs remain exactly 4 groups and 16 unique board words
  when successful.
- composition decisions expose selection and rejection context instead of only
  returning opaque success/failure.
- semantic baseline requests with fixed seed/config now use stable request,
  candidate, puzzle, and trace ids derived from content/signatures.
- semantic baseline mode stays compatible with current service, API, debug, and
  batch-evaluation surfaces.

## Intentionally Deferred

Still deferred beyond Stage 0:

- final ambiguity rejection policy
- final verifier policy and editorial fairness rules
- final scorer/ranker policy
- real lexical/theme/phonetic mainline generators
- calibrated style analysis
- 8-word pool abstractions and paper-style proposal pools

## Risks And Follow-Ups

- The seed dataset is still small and metadata-rich, so this baseline remains a
  deterministic MVP rather than a broad semantic generator.
- Content-derived ids and trace diagnostics improve reproducibility, but batch
  timestamps and run ids may still vary across executions where uniqueness is
  more useful than full byte-for-byte identity.
- Stage 1 should build on the richer evidence emitted here rather than
  replacing the service contracts or treating the baseline heuristics as final
  editorial truth.
