# Connections Puzzle Generator

![Connections Generator Showcase](./showcase.png)

Submission-grade Connections-style puzzle generator with:

- a FastAPI backend
- a React + Vite frontend
- deterministic Stage 0 semantic generation baselines
- Stage 1 ambiguity, verification, and scoring
- Stage 2 lexical and theme diversity
- Stage 3 phonetic generation, style analysis, and calibration artifacts
- Stage 4 release hardening for regression coverage, CI, documentation, and demo readiness

The project is intentionally honest. It implements a real local pipeline and
reproducible evaluation workflow, but it does not claim that final editorial
quality, NYT-likeness, or threshold tuning are solved.

## What Is Implemented

### Generation pipeline

- deterministic feature extraction with semantic, lexical, phonetic, and theme signals
- semantic, lexical, phonetic, and curated-theme `GroupCandidate` generation
- mixed-board composition with semantic-only fallback
- trace metadata, stable ids, and persisted batch-evaluation artifacts

### Quality-control and ranking

- Stage 1 `accept` / `borderline` / `reject` verification decisions
- ambiguity reports with leakage, alternative-group pressure, and cross-group evidence
- interpretable score breakdowns for top-k ranking
- Stage 3 style analysis with local target-band comparisons and threshold diagnostics

### Delivery hardening

- compact regression fixtures for accepted, borderline, and rejected boards
- GitHub Actions CI for lint, format check, tests, frontend build, and eval smoke
- a release summary builder for batch artifacts
- a release-check script for local submission validation

## Quickstart

### Fresh checkout

```bash
cp .env.example .env
make bootstrap
```

`make bootstrap` creates `backend/.venv`, installs backend/frontend dependencies,
and bootstraps the demo data artifacts. No runtime web downloads are required.

### Manual setup

```bash
cp .env.example .env
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
cd ../frontend
npm install
cd ..
backend/.venv/bin/python scripts/bootstrap_demo_data.py
```

## Running Locally

### Backend

```bash
make backend-dev
```

Manual equivalent:

```bash
cd backend
.venv/bin/python -m uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
make frontend-dev
```

Manual equivalent:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Open [http://localhost:5173](http://localhost:5173).

Useful endpoints:

- [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- [http://localhost:8000/api/v1/puzzles/sample](http://localhost:8000/api/v1/puzzles/sample)
- [http://localhost:8000/api/v1/debug/evaluation/latest](http://localhost:8000/api/v1/debug/evaluation/latest)

## Main Commands

### Backend validation

```bash
make lint-backend
make format-check-backend
make test-backend
```

The Ruff targets are intentionally scoped to the Stage 4-maintained Python
paths plus the backend test suite so this hardening pass stays focused on
submission blockers rather than unrelated legacy lint debt.

### Frontend validation

```bash
make typecheck-frontend
make frontend-build
```

### Demo generation

```bash
make demo-generate
```

### Batch evaluation

Demo mode:

```bash
backend/.venv/bin/python scripts/evaluate_batch.py --num-puzzles 10 --top-k 5
```

Stage 3 mixed-generation mode:

```bash
CONNECTIONS_DEMO_MODE=false \
backend/.venv/bin/python scripts/evaluate_batch.py \
  --num-puzzles 10 \
  --top-k 5 \
  --output-dir data/processed/eval_runs/final_stage3_run \
  --no-demo-mode
```

Build a human-readable release summary from a completed run:

```bash
backend/.venv/bin/python scripts/build_release_summary.py \
  --run-dir data/processed/eval_runs/final_stage3_run
```

### Final quality acceptance batch

Pre- or post-calibration acceptance run:

```bash
backend/.venv/bin/python scripts/run_final_quality_acceptance.py \
  --output-dir data/processed/final_quality_acceptance/pre_calibration_run \
  --num-requests 200 \
  --top-k 20 \
  --candidate-pool-limit 30 \
  --base-seed 17
```

This writes:

- the deterministic batch config and seed manifest
- the selected-board summary bundle
- a persisted request-level candidate pool
- `funnel_report.json` and `funnel_report.md`
- `policy_snapshot.json`
- a benchmark audit report copied into the run directory

Compare pre/post runs:

```bash
backend/.venv/bin/python scripts/compare_final_quality_runs.py \
  --before-run data/processed/final_quality_acceptance/pre_calibration_run \
  --after-run data/processed/final_quality_acceptance/post_calibration_run \
  --output-dir data/processed/final_quality_acceptance/reports
```

### Public NYT benchmark normalization

```bash
backend/.venv/bin/python scripts/normalize_nyt_benchmark.py
```

This reads the local public benchmark files under
`data/external/nyt_connections_public/raw/`, normalizes them into canonical
board-level artifacts, and writes deterministic calibration / holdout split
manifests under `data/external/nyt_connections_public/normalized/`.

### NYT quality audit

```bash
backend/.venv/bin/python scripts/run_nyt_quality_audit.py \
  --run-dir data/processed/eval_runs/final_stage3_run
```

This compares generated top-k output against the local public benchmark and
writes machine-readable and human-readable audit reports under
`data/external/nyt_connections_public/reports/`.

### Blind review packet

```bash
backend/.venv/bin/python scripts/build_blind_review_packet.py \
  --run-dir data/processed/final_quality_acceptance/post_calibration_run \
  --generated-count 20 \
  --benchmark-count 20 \
  --seed 17
```

This now writes the packet, answer key, reviewer instructions, and an explicit
`reviewer_template.csv`. If the generated pool is too small, the packet notes
record the shortfall instead of pretending a full 20-board generated sample
exists.

### Solve playtest packet

```bash
backend/.venv/bin/python scripts/build_solve_playtest_packet.py \
  --run-dir data/processed/final_quality_acceptance/post_calibration_run \
  --output-dir data/processed/final_quality_acceptance/solve_playtest \
  --tester-count 5 \
  --boards-per-tester 4 \
  --seed 17
```

### Blind review scoring

```bash
backend/.venv/bin/python scripts/score_blind_review.py \
  --answer-key data/external/nyt_connections_public/review_packets/blind_review_key.json \
  --review-file reviewer_a.csv \
  --review-file reviewer_b.csv
```

If no reviewer files are provided, the script writes an explicit unresolved
final gate instead of a fake pass/fail.

### Solve playtest scoring

```bash
backend/.venv/bin/python scripts/score_solve_playtest.py \
  --packet-key data/processed/final_quality_acceptance/solve_playtest/solve_playtest_key.json \
  --response-file tester_batch_a.csv \
  --output-dir data/processed/final_quality_acceptance/solve_playtest
```

### Release validation

```bash
make release-check
```

This runs the Stage 4 release validation script, including lint, backend tests,
frontend build, a non-demo batch-evaluation smoke run, and release summary
generation.

## Artifact Locations

- `data/processed/eval_runs/<run_id>/`
  Raw batch artifacts such as `summary.json`, `accepted.json`, `rejected.json`,
  `top_k.json`, `calibration_summary.json`, `style_summary.json`,
  `mechanism_mix_summary.json`, `threshold_diagnostics.json`, optional
  `traces.json`, plus Stage 4 `release_summary.json` and `release_summary.md`.
- `data/processed/final_quality_acceptance/<run_name>/`
  Acceptance-sprint bundles including `batch_config.json`, `seed_manifest.json`,
  `policy_snapshot.json`, `candidate_pool.json`, `funnel_report.json`,
  `quality_audit_report.json`, and the usual summary/calibration artifacts.
- `data/processed/release_validation/`
  Local release-check smoke outputs.
- `data/reference/`
  Versioned local calibration targets such as `style_targets_v1.json`.
- `data/external/nyt_connections_public/normalized/`
  Canonical public benchmark boards, manifests, and deterministic split files.

## Quality Claims

The acceptance workflow is intentionally conservative:

- candidate-pool-backed top-k review is a debugging and evaluation surface, not
  proof that the default selected board per request is diverse
- machine publishable proxies and benchmark distances do not satisfy the final
  gate
- the repository should claim the 40% publishable threshold only after real
  blind review forms are scored
- `data/external/nyt_connections_public/reports/`
  Generated-vs-benchmark audit outputs such as `quality_audit_report.json` and
  `quality_audit_report.md`.
- `data/external/nyt_connections_public/review_packets/`
  Blind review packets, answer keys, completed review summaries, and final gate
  outputs.
- `presentation/`
  Presentation and submission support material.

## Tests And Regression Coverage

The backend test suite now includes:

- release fixtures for semantic accepted, mixed accepted, phonetic accepted,
  borderline, and rejected boards
- artifact contract checks for persisted evaluation outputs
- pipeline and evaluation-service integration smoke coverage
- Stage 0, Stage 1, Stage 2, and Stage 3 contract-preservation tests

Run the full backend suite with:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

## CI

GitHub Actions is configured at
[`/.github/workflows/ci.yml`](./.github/workflows/ci.yml) to run:

- Ruff lint
- Ruff format check
- backend pytest
- frontend build
- a lightweight non-demo evaluation smoke run
- release summary generation from the smoke artifacts

## What Remains Provisional

These areas are still explicitly baseline or human-owned:

- final editorial truth for puzzle quality
- broad phonetic coverage beyond the local high-precision inventory
- long-horizon threshold tuning and historical calibration
- claims that style-analysis or NYT-likeness are solved
- claims that generated boards match the NYT benchmark without blind-review evidence

See [`docs/human_owned_components.md`](./docs/human_owned_components.md) for the
module-by-module ownership map.

## Documentation Map

- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/data_schema.md`](./docs/data_schema.md)
- [`docs/evaluation_methodology.md`](./docs/evaluation_methodology.md)
- [`docs/demo_walkthrough.md`](./docs/demo_walkthrough.md)
- [`docs/release_candidate_validation.md`](./docs/release_candidate_validation.md)
- [`docs/submission_checklist.md`](./docs/submission_checklist.md)
- [`docs/ai_usage.md`](./docs/ai_usage.md)
- [`docs/stage3_a_plus_enhancements.md`](./docs/stage3_a_plus_enhancements.md)
- [`docs/stage4_release_hardening.md`](./docs/stage4_release_hardening.md)

## Repository Layout

```text
backend/   FastAPI app, generation pipeline, schemas, services, tests
frontend/  React + TypeScript + Vite UI and developer debug panels
data/      Seed data, reference targets, samples, eval artifacts
docs/      Architecture, schema, evaluation, demo, and submission docs
scripts/   Bootstrap, generation, batch evaluation, release validation helpers
```
