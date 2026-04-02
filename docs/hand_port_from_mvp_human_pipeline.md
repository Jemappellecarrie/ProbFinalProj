# Hand-Port Plan from `origin/feature/mvp-human-pipeline`

## Source Material Inspected

- Branch: `origin/feature/mvp-human-pipeline`
- Explicitly excluded: `8a96144` (`feat: replace scaffold with Intentional Overlap pipeline from arXiv 2407.11240`)
- Pre-replacement commits reviewed:
  - `40eddfe` - human pipeline wiring
  - `63d26e2` - pipeline factory and generation service wiring
  - `989ca44` - ambiguity / verifier / scorer baseline work
  - `ce3c926` - puzzle composer ranking
  - `27c138b` - semantic generator
  - `a0662bd` - feature extraction
  - `45c2c4c` - dependency additions

## Port Strategy

This hand-port keeps the current FastAPI + React repository architecture intact and only brings across reusable ideas that align with the current roadmap order:

1. semantic feature extraction
2. semantic generator
3. puzzle composer
4. optional ambiguity baseline

The branch's useful ideas are being adapted into the existing service-first contracts rather than imported as a competing architecture.

## What Will Be Ported

### 1. Semantic baseline feature extraction

- Target files:
  - `backend/app/features/human_feature_strategy.py`
  - `backend/app/features/semantic_baseline.py`
- Source ideas reused:
  - embedding-oriented feature extraction from `a0662bd`
  - lightweight lexical / phonetic / theme signal enrichment
- Adaptation:
  - replace direct `sentence-transformers` model loading with a deterministic, typed semantic-sketch baseline that works inside the existing repository contracts
  - keep provenance, versioning, and debug evidence explicit
- Rationale:
  - preserves the branch's "attach reusable semantic evidence to each word" idea without introducing hidden runtime downloads or infrastructure coupling

### 2. First real semantic generator

- Target files:
  - `backend/app/generators/semantic.py`
- Source ideas reused:
  - centroid / similarity-driven grouping from `27c138b`
  - confidence computed from local semantic cohesion
- Adaptation:
  - generate only valid 4-word `GroupCandidate` objects
  - prefer interpretable shared-tag / shared-signal group formation over opaque clustering
  - include traceable evidence and local confidence metadata
- Rationale:
  - keeps the useful semantic grouping logic while fitting the mainline `GroupCandidate` schema and current explainability goals

### 3. Semantic-heavy composer baseline

- Target files:
  - `backend/app/pipeline/builder.py`
- Source ideas reused:
  - confidence-based ranking from `ce3c926`
- Adaptation:
  - preserve current `PuzzleCandidate` contracts
  - rank combinations with transparent compatibility notes, semantic preference, and duplicate / overlap avoidance
  - do not import the branch tip's overlap-assignment pipeline
- Rationale:
  - delivers the first real puzzle assembly stage without replacing the scaffold or jumping ahead to a harder editorial objective

### 4. Optional experimental ambiguity baseline

- Target files:
  - `backend/app/solver/human_ambiguity_strategy.py`
- Source ideas reused:
  - cross-group cosine leakage heuristic from `989ca44`
- Adaptation:
  - keep the logic explicitly labeled as experimental / provisional
  - integrate through existing `AmbiguityReport` / `VerificationResult` structures
  - leave final editorial ambiguity policy human-owned
- Rationale:
  - useful as a transparent baseline signal for debug views and batch evaluation, but not presented as solved truth

### 5. Pipeline wiring into current architecture

- Target files:
  - `backend/app/pipeline/semantic_pipeline.py`
  - `backend/app/services/generation_service.py`
  - `backend/app/services/evaluation_service.py`
- Source ideas reused:
  - dedicated non-demo pipeline factory from `63d26e2`
- Adaptation:
  - keep demo mode as the stable default
  - wire an opt-in semantic baseline pipeline behind existing service entrypoints
  - preserve current API shapes, traces, batch evaluation artifacts, and frontend-compatible payloads
- Rationale:
  - allows the repository to expose a real semantic path without destabilizing the current demo shell

## What Will Be Marked Experimental / Baseline

- semantic-sketch vectors and cosine similarity features
- semantic candidate confidence scores
- composer compatibility scoring
- ambiguity / leakage heuristics

These will be documented as baseline or experimental implementations, not as final editorial truth.

## Not Ported on Purpose

- the branch tip's `generate_puzzle.py` single-file architecture
- the root `requirements.txt` workflow
- direct environment-variable reads or direct client construction inside core logic
- the 8-word pool as a mainline `GroupCandidate` abstraction
- intentional-overlap assignment as the default composer
- the branch verifier's hard gate requiring multiple group types
- scorer / verifier formulas that would overstate what is already solved
- hidden model or corpus downloads in the generation hot path

## Expected Repository Touch Points

- `README.md`
- `docs/human_owned_components.md`
- `backend/app/features/human_feature_strategy.py`
- `backend/app/features/semantic_baseline.py`
- `backend/app/generators/semantic.py`
- `backend/app/pipeline/builder.py`
- `backend/app/pipeline/semantic_pipeline.py`
- `backend/app/services/generation_service.py`
- `backend/app/services/evaluation_service.py`
- `backend/app/solver/human_ambiguity_strategy.py`
- backend tests covering feature extraction, semantic generation, composition, ambiguity, and service-level generation
