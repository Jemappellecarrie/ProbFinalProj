# Evaluation Methodology

## Purpose

The evaluation workflow is an offline review loop for the existing Stage 0 to
Stage 3 pipeline. It is designed to make generated boards inspectable and
reproducible, not to hide a black-box optimizer.

## Decision Classes

The verifier emits three decision classes:

- `accept`
  Structurally valid boards with controlled ambiguity pressure and no hard
  reject reasons.
- `borderline`
  Playable boards that still trigger meaningful Stage 1 or Stage 3 warnings,
  such as weak group support, solver disagreement, monotony, or elevated
  ambiguity pressure below the hard reject threshold.
- `reject`
  Boards with structural failures, severe ambiguity pressure, or clearly weak
  group support.

`passed=true` means the decision is either `accept` or `borderline`.

## Top-K Ranking

Accepted and borderline boards are ranked using the Stage 1 top-k ordering:

1. verification decision class
2. overall score
3. ambiguity penalty
4. composer ranking score
5. stable puzzle id

This policy is intentionally explicit in the persisted artifacts and tests.

## How To Run Evaluation

Demo-mode smoke run:

```bash
backend/.venv/bin/python scripts/evaluate_batch.py --num-puzzles 10 --top-k 5
```

Stage 3 mixed-generation evaluation:

```bash
CONNECTIONS_DEMO_MODE=false \
backend/.venv/bin/python scripts/evaluate_batch.py \
  --num-puzzles 10 \
  --top-k 5 \
  --output-dir data/processed/eval_runs/final_stage3_run \
  --no-demo-mode
```

Final quality acceptance batch:

```bash
backend/.venv/bin/python scripts/run_final_quality_acceptance.py \
  --output-dir data/processed/final_quality_acceptance/pre_calibration_run \
  --num-requests 200 \
  --top-k 20 \
  --candidate-pool-limit 30 \
  --base-seed 17
```

Human-readable release bundle:

```bash
backend/.venv/bin/python scripts/build_release_summary.py \
  --run-dir data/processed/eval_runs/final_stage3_run
```

Public benchmark normalization:

```bash
backend/.venv/bin/python scripts/normalize_nyt_benchmark.py
```

Generated-versus-benchmark quality audit:

```bash
backend/.venv/bin/python scripts/run_nyt_quality_audit.py \
  --run-dir data/processed/eval_runs/final_stage3_run
```

Blind review packet generation:

```bash
backend/.venv/bin/python scripts/build_blind_review_packet.py \
  --run-dir data/processed/eval_runs/final_stage3_run \
  --generated-count 10 \
  --benchmark-count 10 \
  --seed 17
```

Blind review scoring:

```bash
backend/.venv/bin/python scripts/score_blind_review.py \
  --answer-key data/external/nyt_connections_public/review_packets/blind_review_key.json \
  --review-file reviewer_a.csv \
  --review-file reviewer_b.csv
```

Solve-playtest packet generation:

```bash
backend/.venv/bin/python scripts/build_solve_playtest_packet.py \
  --run-dir data/processed/final_quality_acceptance/post_calibration_run \
  --output-dir data/processed/final_quality_acceptance/solve_playtest \
  --tester-count 5 \
  --boards-per-tester 4 \
  --seed 17
```

Solve-playtest scoring:

```bash
backend/.venv/bin/python scripts/score_solve_playtest.py \
  --packet-key data/processed/final_quality_acceptance/solve_playtest/solve_playtest_key.json \
  --response-file tester_batch_a.csv \
  --output-dir data/processed/final_quality_acceptance/solve_playtest
```

## Persisted Artifact Bundle

Each run writes a stable artifact bundle under `data/processed/eval_runs/<run_id>/`.

Required files:

- `config.json`
- `summary.json`
- `accepted.json`
- `rejected.json`
- `top_k.json`
- `calibration_summary.json`
- `style_summary.json`
- `mechanism_mix_summary.json`
- `threshold_diagnostics.json`

Optional file:

- `traces.json`

Stage 4 summary files:

- `release_summary.json`
- `release_summary.md`

Final quality acceptance files:

- `batch_config.json`
- `seed_manifest.json`
- `policy_snapshot.json`
- `candidate_pool.json`
- `funnel_report.json`
- `funnel_report.md`
- `quality_audit_report.json`
- `quality_audit_report.md`

## Reading The Outputs

### `summary.json`

Use this as the high-level run overview:

- accepted versus rejected counts
- generator-family usage
- score distribution
- ambiguity-risk distribution
- solver-agreement summary
- embedded `top_k` and `calibration_summary`

### `accepted.json` and `rejected.json`

Use these when you need record-level review:

- board words and labels
- mechanism mix
- verifier decision
- score breakdown
- ambiguity report
- style analysis
- selected pipeline components

### `top_k.json`

Use this for demo or grading review of the best current boards. In the final
quality acceptance workflow, `top_k.json` is drawn from the persisted
request-level candidate pool rather than only the single selected winner from
each request. It preserves:

- rank
- decision class
- score breakdown
- ambiguity risk
- solver agreement
- style archetype and alignment
- mechanism mix

### Calibration artifacts

These are Stage 3 review aids, not claims of solved style modeling:

- `calibration_summary.json`
  Full aggregate summary across accepted, rejected, and top-k slices.
- `style_summary.json`
  Style-metric slice summaries.
- `mechanism_mix_summary.json`
  Mechanism-distribution slice summaries.
- `threshold_diagnostics.json`
  Individual drift diagnostics for review.

### Final quality acceptance artifacts

- `candidate_pool.json`
  Persisted request-level candidate boards surfaced for ranking and funnel
  analysis.
- `funnel_report.json`
  Deterministic yield, uniqueness, reject-reason, and collapse diagnostics.
- `policy_snapshot.json`
  Exact Stage 1, Stage 2, and Stage 3 policy knobs used for the run.

## Interpreting Style And Calibration

Style-analysis outputs are additive and descriptive:

- `archetype` and `board_archetype`
  Coarse labels for the board profile.
- `style_alignment_score`
  A local baseline alignment score against versioned target bands.
- `out_of_band_flags`
  Signals that a board or slice drifts outside the current local target bands.
- `threshold_diagnostics`
  Evidence-backed warnings about drift, overrepresentation, underrepresentation,
  or unusual score behavior.

These outputs should guide review. They should not be treated as final
editorial truth.

## Public NYT Benchmark Audit

The repository now supports an external audit layer built from a local public
benchmark export. The primary canonical source is the local Hugging Face export
of `eric27n/NYT-Connections`. A local GitHub mirror may repair missing primary
fields or add explicitly supplemental newer boards, but it does not replace the
primary source for difficulty ordering.

The benchmark workflow is intentionally local and reproducible:

- normalize raw public files into deterministic board-level artifacts
- build explicit calibration / holdout split manifests by puzzle date
- compare generated top-k slices against benchmark holdout slices
- generate a source-hidden blind review packet
- score completed human reviews into a publishable-rate summary

This project does not scrape the official NYT archive.

## Blind Review Gate

The default delivery gate is intentionally human-owned:

- generated output is `quality-ready` only if at least 40% of reviewed
  generated boards are marked publishable / NYT-like by a majority of reviewers

Automatic audit metrics can highlight closeness to the public benchmark, but
they do not satisfy that gate by themselves.

If no real reviewer files are provided, the final gate must remain
`unresolved`.

## What Good Batch Output Looks Like

Healthy batch output usually shows:

- at least some accepted or borderline boards
- interpretable mechanism mix rather than a single opaque generator family
- low ambiguity among the top-k boards
- style and calibration diagnostics that are understandable from the raw JSON
- reproducible reruns for the same seeds and fixed local data

## Known Limits

- Accepted output is still heuristic, not editorially final.
- Thresholds and target bands are local baselines.
- A good top-k run does not prove final NYT-level quality.
- Human review is still required for submission claims about puzzle quality.
- Benchmark-side mechanism labels are conservative audit heuristics, not gold
  editorial annotations.
