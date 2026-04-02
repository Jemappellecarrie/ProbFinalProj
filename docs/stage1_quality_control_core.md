# Stage 1 Quality-Control Core

## Scope

Stage 1 adds the first real quality-control policy layer on top of the Stage 0
semantic baseline. It keeps the existing service-first pipeline, typed schemas,
trace/debug payloads, and deterministic semantic generation contracts intact
while making ambiguity analysis, verification, and ranking materially useful.

This stage is limited to:

- evidence-rich semantic ambiguity analysis on composed 16-word boards
- explicit Stage 1 verification decisions: `accept`, `borderline`, `reject`
- interpretable puzzle scoring for batch ranking and top-k inspection
- additive schema/report enrichment for traces, evaluation artifacts, and debug views

This stage does not claim that editorial truth, final fairness policy, or
historical style calibration are solved.

## Planned File Changes

- `backend/app/schemas/evaluation_models.py`
- `backend/app/schemas/puzzle_models.py`
- `backend/app/solver/human_ambiguity_strategy.py`
- `backend/app/solver/verifier.py`
- `backend/app/scoring/human_scoring_strategy.py`
- `backend/app/pipeline/semantic_pipeline.py`
- `backend/app/pipeline/orchestration.py`
- `backend/app/services/evaluation_service.py`
- `backend/tests/test_semantic_baseline.py`
- `backend/tests/test_pipeline.py`
- `backend/tests/test_evaluation_service.py`
- `backend/tests/test_schemas.py`
- `backend/tests/test_human_owned_placeholders.py`
- `README.md`
- `docs/architecture.md`
- `docs/human_owned_components.md`

## Ambiguity Signals

Stage 1 ambiguity analysis will derive signals from existing Stage 0 feature and
group evidence:

- per-group coherence from group confidence, member scores, pairwise similarity,
  and leave-one-out word-to-group fit
- per-word leakage from assigned-group fit versus strongest competing-group fit
- cross-group leakage summaries from directional group-to-group fit pressure
- suspicious alternative 4-word groups by enumerating all `C(16, 4)` board
  combinations, excluding true groups, and ranking mixed-source combinations by
  coherence, shared-signal support, and spread across true groups
- compact board-level pressure metrics and deterministic warning flags

## Verification Policy Outline

The verifier will combine structural checks, solver status, and Stage 1
ambiguity evidence into a deterministic policy:

- `reject`
  for structural invalidity, severe ambiguity pressure, or clearly implausible
  / weak group support
- `borderline`
  for puzzles that remain playable but show moderate leakage, uneven group
  quality, or suspicious alternative groups below hard-reject thresholds
- `accept`
  for puzzles with solid group support, controlled leakage, and no strong
  misleading alternative groups

`VerificationResult` will stay backward compatible through `passed`, while
adding an explicit decision, warning flags, summary metrics, and stable evidence
references.

## Scoring Breakdown Outline

Accepted and borderline puzzles will be ranked with an interpretable Stage 1
score composed from:

- group coherence quality
- board balance / weakest-group support
- evidence quality / interpretability
- ambiguity penalty
- leakage penalty
- alternative-group penalty

The overall score will remain monotonic and transparent: better coherence helps,
while stronger ambiguity pressure hurts. Ranking will prefer decision class
first, then overall score, then lower ambiguity pressure, then composer score,
then stable id.

## Deferred To Stage 2+

Still intentionally deferred:

- lexical/theme/phonetic generator upgrades
- style calibration or broad NYT-likeness modeling
- historical benchmark calibration workflows
- richer editorial fairness policy beyond Stage 1 thresholds
- 8-word proposal pools or overlap-first generation architectures
- any claim that ambiguity or ranking is “solved”
