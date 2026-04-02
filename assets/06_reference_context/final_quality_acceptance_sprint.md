# Final Quality Acceptance Sprint

## Current Status

The repository already includes the Stage 0 to Stage 4 generator pipeline, the
public NYT benchmark normalization flow, blind review packet generation, and a
40% publishable / NYT-like human gate. Current evidence is not sufficient to
claim quality readiness:

- the latest stored benchmark audit reviewed only 1 generated top-k board
- that board landed in `accepted_borderline`
- the machine publishable proxy was `0.0`
- the generated-versus-benchmark comparison still showed large distribution gaps

This sprint exists to measure the current system honestly, diagnose where yield
collapses, make one narrow calibration pass, and prepare the human review path.

## Scope

This sprint preserves the existing architecture and modeling pipeline:

- FastAPI backend, React frontend, typed schemas, and service-first wiring stay
  intact
- Stage 0 to Stage 4 generation, verification, scoring, and style analysis stay
  intact
- the local normalized public NYT benchmark remains the benchmark source

This sprint does not add new generators, new datasets, new runtime
dependencies, or a new modeling architecture.

## Fixed Batch Plan

Use one deterministic fixed batch configuration for before/after comparison:

- default batch size: `200` generation requests
- minimum fallback batch size: `100` generation requests if runtime is
  materially prohibitive after calibration widens the candidate pool
- deterministic seed manifest persisted to disk
- fixed output roots under
  `data/processed/final_quality_acceptance/<run_slug>/`

Each run must persist:

- exact batch config
- seed manifest
- raw evaluation artifacts
- funnel diagnostics
- benchmark audit outputs

Primary command:

```bash
backend/.venv/bin/python scripts/run_final_quality_acceptance.py \
  --output-dir data/processed/final_quality_acceptance/pre_calibration_run \
  --num-requests 200 \
  --top-k 20 \
  --candidate-pool-limit 30 \
  --base-seed 17
```

Compare runs:

```bash
backend/.venv/bin/python scripts/compare_final_quality_runs.py \
  --before-run data/processed/final_quality_acceptance/pre_calibration_run \
  --after-run data/processed/final_quality_acceptance/post_calibration_run \
  --output-dir data/processed/final_quality_acceptance/reports
```

## Funnel Metrics

The sprint must compute and persist at least:

- total generation requests
- total puzzle candidates seen
- structurally valid vs structurally invalid boards
- unique board count vs duplicate board count
- accepted / borderline / rejected counts and percentages
- accepted / borderline / rejected unique counts
- reject reason and warning-flag breakdowns
- mechanism mix by decision class
- semantic-only vs mixed vs phonetic-inclusive counts
- top-k unique count
- repeated board-signature and mechanism-signature concentration

The funnel report should explicitly diagnose whether the bottleneck is:

- low generator diversity
- over-aggressive verifier thresholds
- ranking collapse
- dedupe collapse
- composer mix collapse
- or a combination

## Allowed Calibration Knobs

Only narrow, explainable constants may change:

- Stage 1 verifier thresholds
- Stage 1 or Stage 3 scoring weights
- diversity bonuses or redundancy penalties
- dedupe signatures and top-candidate selection limits
- candidate caps and small composer selection constants
- small style-policy thresholds already exposed in core policy modules

The sprint must document each changed knob and preserve a before/after diff.

The implemented calibration lane is intentionally narrow:

- Stage 2 composer candidate cap
- Stage 2 ranked-candidate cap
- Stage 2 near-duplicate board overlap cap

## Human Review Preconditions

Human blind review is only meaningful when the post-calibration run produces a
large enough and diverse enough candidate pool. The sprint will compute and
report explicit readiness checks, including:

- at least `50` unique generated boards total
- at least `20` unique accepted or borderline boards
- at least `20` unique review-ready generated boards after dedupe

If these checks fail, the sprint must say the system is not ready for a fair
blind review packet of 20 generated boards.

If the calibrated run saturates its unique top-review pool after only a handful
of deterministic requests, that saturation should be reported explicitly rather
than hidden behind a longer batch count.

## Final Gate

The final project gate remains human-owned:

- generated output is quality-ready only if at least `40%` of reviewed
  generated boards are marked publishable / NYT-like by a majority of
  reviewers

Machine proxies can support prioritization, but they do not satisfy the gate.

## Manual Human Steps

The repository can prepare materials and score completed forms, but humans must
still:

- complete blind review forms
- complete solve playtest logs
- provide reviewer files back to the scoring scripts

If real reviewer inputs are missing, the sprint must report the final gate as
unresolved rather than passed.
