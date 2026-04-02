# NYT Benchmark Quality Audit

## Purpose

This repository now treats a local public NYT Connections dataset as an
external benchmark for audit, calibration, and blind review scaffolding. The
goal is not to claim parity with the NYT archive. The goal is to make that
claim testable with reproducible local evidence.

## Data Sources

- Primary canonical source: local Hugging Face export of
  `eric27n/NYT-Connections`
- Preferred raw paths:
  - `data/external/nyt_connections_public/raw/nyt_connections_hf.parquet`
  - `data/external/nyt_connections_public/raw/nyt_connections_hf.csv`
- Optional supplement: local GitHub JSON mirror at
  `data/external/nyt_connections_public/raw/nyt_connections_answers_github.json`

The Hugging Face dataset remains the primary source for benchmark identity,
dates, levels, and difficulty ordering. The GitHub mirror is used only to
repair missing primary fields or add explicitly supplemental newer boards.

## Normalization Plan

- Read raw benchmark files only from local disk.
- Normalize row-level Hugging Face data into deterministic board-level records.
- Preserve board date, source ids, 16 words, 4 groups, group labels, levels,
  colors, and tile positions when available.
- Generate deterministic board and solution signatures plus explicit provenance.
- Validate invariants:
  - exactly 16 board words
  - exactly 4 groups
  - 4 words per group
  - unique board words
  - valid level range when present
- Record integrity issues in a manifest instead of hiding them.

## Split Strategy

- Sort primary benchmark boards deterministically by `puzzle_date`,
  `benchmark_board_id`.
- Calibration split: oldest 80% of primary boards.
- Holdout split: newest 20% of primary boards.
- Freshness split: supplement-only boards newer than the primary benchmark max
  date, if present locally.

This keeps calibration tied to stable historical data while preserving a newer
holdout and an explicitly separate freshness lane.

## Automatic Comparison Metrics

- Generated batch verifier decision distribution versus benchmark re-evaluation
  distribution
- Score and ambiguity summaries
- Mechanism mix and inferred semantic / lexical / phonetic / theme proportions
- Style-target distance and out-of-band summaries
- Label-length and label-shape summaries
- Monotony, diversity, and board archetype summaries
- Top-k quality bucket rates:
  - `accepted_high_confidence`
  - `accepted_borderline`
  - `rejected`

Benchmark-side verifier and scorer summaries will use the existing Stage 1 and
Stage 3 pipeline with an answer-aware local reference solver and conservative
heuristic mechanism labeling. These outputs are audit aids, not editorial truth.

## Blind Review Workflow

- Build a deterministic mixed packet from generated top-k boards and benchmark
  holdout boards.
- Hide source identity from reviewer-facing ids and filenames.
- Export reviewer JSON/CSV plus instructions.
- Score completed review forms into publishable-rate summaries, generated versus
  benchmark comparisons, and a final gate result.

## Quality Gate

Default delivery gate:

- `quality_ready = true` only when at least 40% of reviewed generated boards
  are marked publishable / NYT-like by a majority of reviewers.

This gate is intentionally human-rating-based. Automatic audit metrics can
support prioritization, but they do not satisfy the publishable-rate claim on
their own.

## Intentionally Deferred

- Any claim that the generator matches NYT editorial quality
- Runtime scraping or web dependence
- Modeling rewrites to generators, composer, verifier, or scorer
- Rich semantic mechanism labeling beyond conservative audit heuristics
- Replacing human review with automatic scoring
