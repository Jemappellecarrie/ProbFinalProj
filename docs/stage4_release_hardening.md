# Stage 4 Release Hardening

## Scope

Stage 4 turns the existing Stage 0 through Stage 3 pipeline into a
submission-grade repository without reopening the modeling problem. This pass
focuses on reproducibility, regression protection, CI/local validation,
evaluation interpretability, frontend/debug wording alignment, and final
submission documentation.

## Planned File Areas

- `backend/tests/fixtures/`
- `backend/tests/test_release_regressions.py`
- `backend/tests/test_evaluation_service.py`
- `backend/tests/test_pipeline.py`
- `frontend/src/components/*`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/types/puzzle.ts`
- `frontend/package.json`
- `frontend/tsconfig*.json`
- `.github/workflows/ci.yml`
- `Makefile`
- `scripts/evaluate_batch.py`
- `scripts/build_release_summary.py`
- `scripts/release_check.py`
- `README.md`
- `docs/architecture.md`
- `docs/data_schema.md`
- `docs/evaluation_methodology.md`
- `docs/ai_usage.md`
- `docs/demo_walkthrough.md`
- `docs/submission_checklist.md`
- `docs/release_candidate_validation.md`

## Regression Strategy

- Add compact, versioned fixture packs for five board classes:
  accepted semantic-heavy, accepted mixed, accepted phonetic-inclusive,
  borderline, and reject.
- Assert verifier decision, core score ordering semantics, mechanism mix,
  style-analysis presence, calibration presence, and trace/debug invariants
  without relying on giant snapshots.
- Add artifact-contract tests for persisted evaluation outputs so Stage 4 keeps
  `summary.json`, `accepted.json`, `rejected.json`, `top_k.json`, and the Stage
  3 calibration artifacts stable and readable.

## CI And Workflow Strategy

- Add a GitHub Actions workflow that runs backend lint, backend format check,
  backend tests, frontend build/typecheck smoke, and a lightweight non-demo
  batch-evaluation smoke command.
- Add a repo-level release validation helper so a grader or teammate can run
  one command for the final submission checks.
- Tighten local developer commands in the `Makefile` and README so the default
  happy path uses explicit, low-friction commands from a fresh checkout.

## Docs And AI Usage Deliverables

- Finalize the README around setup, backend/frontend runs, testing, evaluation,
  artifact locations, and the current Stage 0 to Stage 3 baseline.
- Add explicit evaluation methodology, demo walkthrough, submission checklist,
  and release-validation docs.
- Add exhaustive Stage 4 AI-usage documentation that distinguishes generated
  outputs from human review and preserves honest claims about provisional
  thresholds, style targets, and unresolved editorial judgment.

## Frontend And Debug Polish Goals

- Remove Stage 2-era or scaffold-era wording that under-describes the current
  phonetic, style-analysis, calibration, and mixed-board behavior.
- Make the developer-facing UI surface verification decision, mechanism mix,
  score components, style warnings, and calibration context without a frontend
  redesign.
- Keep backend-to-frontend contract changes additive and backwards-compatible.

## Intentionally Deferred

- New generator families, new external datasets, or broader knowledge systems
- Large verifier/scoring threshold redesigns
- Architectural rewrites or production-service concerns beyond local
  reproducibility and demo readiness
- Claims that the current heuristics represent final editorial truth
