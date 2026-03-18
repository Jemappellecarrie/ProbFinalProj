# Connections Puzzle Generator

Production-style scaffold for a NYT-Connections-style puzzle generator, with a deliberate split between runnable demo infrastructure and intentionally human-owned quality logic.

## What This Repository Contains

- A FastAPI backend with typed schemas, pipeline orchestration, repositories, mock/demo generation components, and explicit human-owned strategy stubs.
- A React + TypeScript + Vite frontend that can request a generated demo puzzle, reveal groups, inspect scoring, and show debug traces.
- A second-stage quality-control scaffold for solver ensembles, ambiguity reports, style-analysis placeholders, and batch evaluation artifacts.
- Seed/sample data, bootstrap scripts, developer tooling, and architecture documentation.
- Clear seams for the project-defining logic that should remain owned by a human researcher/architect.

## Guiding Principle

The repository runs end-to-end in demo mode, but it does **not** pretend the hard parts are solved. High-value puzzle quality logic is left as explicit placeholders with `TODO[HUMAN_*]` markers, rich docstrings, and either `NotImplementedError` or clearly labeled baseline implementations.

## Quickstart

1. Copy `.env.example` to `.env` if you want local overrides.
2. Install backend dependencies:

```bash
cd backend
python3 -m pip install -e ".[dev]"
```

3. Install frontend dependencies:

```bash
cd frontend
npm install
```

4. Bootstrap demo feature artifacts:

```bash
python3 scripts/bootstrap_demo_data.py
```

5. Start the backend:

```bash
make backend-dev
```

6. Start the frontend in another terminal:

```bash
make frontend-dev
```

7. Open [http://localhost:5173](http://localhost:5173).

## Demo Mode

Demo mode is enabled by default through `CONNECTIONS_DEMO_MODE=true`.

In demo mode the system:

- Loads seed words from JSONL.
- Uses a baseline feature extractor with deterministic mock signals.
- Uses mock group generators for semantic, lexical, phonetic, and theme buckets.
- Composes a 16-word puzzle from one group of each type.
- Runs a stub solver/verifier.
- Scores the result with a transparent baseline scorer.
- Exposes debug metadata so future human-owned strategies can be evaluated against the same pipeline.
- Supports offline batch evaluation with accepted/rejected/top-k persistence.

## Human-Owned Implementation Map

The following modules are intentionally scaffolded but not solved:

- `backend/app/features/human_feature_strategy.py`
- `backend/app/generators/semantic.py` (`HumanSemanticGroupGenerator`)
- `backend/app/generators/lexical.py` (`HumanLexicalGroupGenerator`)
- `backend/app/generators/phonetic.py` (`HumanPhoneticGroupGenerator`)
- `backend/app/generators/theme.py` (`HumanThemeGroupGenerator`)
- `backend/app/pipeline/builder.py` (`HumanPuzzleComposer`)
- `backend/app/solver/human_ambiguity_strategy.py`
- `backend/app/solver/verifier.py` (`InternalPuzzleVerifier`)
- `backend/app/scoring/style_analysis.py` (`HumanStyleAnalyzer`)
- `backend/app/scoring/human_scoring_strategy.py`

See [docs/human_owned_components.md](/Users/zoe/ProbFinal/ProbFinalProj/docs/human_owned_components.md) for the exact file/function checklist.

## Repository Layout

```text
backend/   FastAPI application, pipeline, schemas, tests
frontend/  React + TypeScript + Vite UI shell
data/      Seed words, processed artifacts, sample payloads
docs/      Architecture, schemas, API contract, roadmap
scripts/   Demo bootstrap and local run helpers
```

## Suggested Next Steps

1. Replace mock feature extraction with curated strategies.
2. Implement human-owned group generators one module at a time.
3. Replace baseline ambiguity checks with real alternative-grouping analysis.
4. Implement final ranking formulas and offline evaluation loops.
5. Replace baseline solver ensemble and style-analysis scaffolds with human-owned logic.

## Development Commands

- `make bootstrap-demo`
- `make backend-dev`
- `make frontend-dev`
- `make demo-generate`
- `make evaluate-batch`
- `make test-backend`
- `make lint-backend`
- `make typecheck-frontend`
