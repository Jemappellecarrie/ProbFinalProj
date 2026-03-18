# Connections Puzzle Generator

![Connections Generator Showcase](./showcase.png)

End-to-end product showcase for the current repository state: demo puzzle generation, reveal flow, score inspection, ambiguity/debug outputs, and top-k batch-evaluation browsing.

Production-style scaffold for a NYT-Connections-style puzzle generator. The repository now has:

- a first-stage end-to-end demo generation pipeline
- a second-stage quality-control scaffold for ambiguity modeling, solver ensemble analysis, style-analysis hooks, batch evaluation, and top-k debug browsing

The project is intentionally honest: demo mode runs end-to-end, but the project-defining puzzle-quality heuristics remain human-owned and explicitly unimplemented.

## Product Showcase

The image above reflects the current developer-facing product shell for this repository.

### What the showcase demonstrates

- a playable demo-style puzzle board with 16 words arranged in a mixed board layout
- solution reveal panels showing the four hidden groups and their metadata
- a score panel with coherence, ambiguity penalty, leakage estimate, and style-analysis placeholder values
- a developer debug panel that surfaces ambiguity reports, solver ensemble output, style-analysis output, and generation trace data
- a Top-K panel that reads persisted batch-evaluation results and lets you inspect the current best accepted puzzles

### Product surfaces currently scaffolded

- `Generate Puzzle`
  Runs the current demo pipeline through FastAPI and returns a generated puzzle payload.
- `Load Static Sample`
  Loads a bundled sample payload for stable UI and API contract inspection.
- `Reveal Answers`
  Shows group labels, rationales, and grouped words for the current puzzle.
- `Developer Mode`
  Displays ensemble disagreement, ambiguity evidence, style signals, and latest batch-evaluation summary.
- `Batch Evaluation Outputs`
  Persists accepted puzzles, rejected puzzles, top-k rankings, summary metrics, and optional traces under `data/processed/eval_runs/`.


## Current Scope

### Generation scaffold

- FastAPI backend with typed schemas, repositories, orchestration, generators, solver, verifier, and scorer wiring
- React + TypeScript + Vite frontend for puzzle generation, reveal, score inspection, and developer-mode debug views
- seed/sample/demo data plus bootstrap and local run scripts

### Second-stage quality-control scaffold

- ambiguity evidence models and baseline ambiguity reports
- solver registry plus ensemble coordinator
- baseline second solver for agreement/disagreement exercise
- style-analysis placeholder reports
- offline batch evaluation with accepted/rejected/top-k persistence
- debug endpoint and frontend Top-K inspection panel

## Guiding Principle

This repository does **not** claim that ambiguity detection, NYT-likeness, ranking quality, or final solver behavior are solved.

Anything project-defining remains clearly marked with `TODO[HUMAN_*]`, rich docstrings, and either:

- a human-owned stub
- a baseline/mock implementation explicitly labeled as provisional

## Local Setup

### 1. Copy environment variables

```bash
cp .env.example .env
```

### 2. Create a backend Python environment

Recommended: use `venv` inside `backend/`.

```bash
cd backend
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```


### 3. Install frontend dependencies

```bash
cd ../frontend
npm install
```

### 4. Bootstrap demo artifacts

```bash
cd ..
python3 scripts/bootstrap_demo_data.py
```

## Running Locally

Use two terminals.

### Terminal 1: backend

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Then open [http://localhost:5173](http://localhost:5173).

Useful backend URLs:

- [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- [http://localhost:8000/api/v1/puzzles/sample](http://localhost:8000/api/v1/puzzles/sample)
- [http://localhost:8000/api/v1/debug/evaluation/latest](http://localhost:8000/api/v1/debug/evaluation/latest)

## Demo Mode

Demo mode is enabled by default through `CONNECTIONS_DEMO_MODE=true`.

In demo mode the system:

- loads seed words from JSONL
- extracts baseline mock features
- produces mock semantic / lexical / phonetic / theme groups
- composes a 16-word puzzle
- runs a solver ensemble scaffold
- emits a baseline ambiguity report
- emits a baseline style-analysis report
- scores the puzzle with a transparent mock scorer
- supports offline batch evaluation and top-k persistence

## Batch Evaluation

Run a batch evaluation:

```bash
python3 scripts/evaluate_batch.py --num-puzzles 10 --top-k 5
```

Artifacts are written under:

```text
data/processed/eval_runs/<run_id>/
```

Typical outputs:

- `config.json`
- `summary.json`
- `accepted.json`
- `rejected.json`
- `top_k.json`
- `traces.json` when traces are enabled

## Human-Owned Implementation Map

The following modules are intentionally scaffolded but not solved:

- `backend/app/features/human_feature_strategy.py`
- `backend/app/generators/semantic.py`
- `backend/app/generators/lexical.py`
- `backend/app/generators/phonetic.py`
- `backend/app/generators/theme.py`
- `backend/app/pipeline/builder.py`
- `backend/app/solver/human_ambiguity_strategy.py`
- `backend/app/solver/verifier.py` via `InternalPuzzleVerifier`
- `backend/app/scoring/style_analysis.py` via `HumanStyleAnalyzer`
- `backend/app/scoring/human_scoring_strategy.py`

See [`docs/human_owned_components.md`](docs/human_owned_components.md) for the exact ownership map.

## Repository Layout

```text
backend/   FastAPI app, pipeline, schemas, services, solver/scoring scaffolds, tests
frontend/  React + TypeScript + Vite UI shell and developer-facing debug panels
data/      Seed words, processed artifacts, sample payloads, evaluation runs
docs/      Architecture, schemas, API contract, TODO maps
scripts/   Bootstrap, demo generation, batch evaluation, local run helpers
```

## Key Docs

- [`docs/architecture.md`](docs/architecture.md) - architecture and pipeline overview
- [`docs/api_contract.md`](docs/api_contract.md) - backend API shapes and debug endpoint notes
- [`docs/data_schema.md`](docs/data_schema.md) - schema reference for puzzle, trace, ambiguity, ensemble, style, and batch models
- [`docs/human_owned_components.md`](docs/human_owned_components.md) - exact human-owned modules, functions, and responsibilities

## Development Commands

- `make bootstrap-demo`
- `make backend-dev`
- `make frontend-dev`
- `make demo-generate`
- `make evaluate-batch`
- `make test-backend`
- `make lint-backend`
- `make typecheck-frontend`
