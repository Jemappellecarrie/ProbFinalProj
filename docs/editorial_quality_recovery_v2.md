# Editorial Quality Recovery V2

## Scope

This pass is a focused editorial-quality recovery on top of the existing Stage 0-4 system and the existing editorial recovery layer.

It is intentionally not:

- a new generator expansion pass
- a new modeling stage
- a broad architecture rewrite
- a benchmark-contaminating optimization pass

The architecture stays intact:

- FastAPI backend
- React frontend
- typed schemas and persisted artifacts
- Stage 0-4 pipeline flow
- benchmark audit layer
- blind review and solve-playtest tooling

## Current Failure Mode After Recovery V1

The current system improved machine-side acceptance quality, but it did so by collapsing the run onto a tiny editorial neighborhood.

Observed from the current deterministic recovery lane in [`data/processed/final_quality_acceptance/editorial_recovery_run`](/Users/zoe/ProbFinal/ProbFinalProj/data/processed/final_quality_acceptance/editorial_recovery_run):

- `200` generation requests
- `1600` persisted candidate-pool records
- only `8` unique boards
- only `8` unique editorial families
- `repeated_family_rate = 1.0`
- `repeated_surface_wordplay_family_count = 7`
- top-k mechanism mix average:
  - `semantic_group_count = 2.25`
  - `theme_group_count = 0.875`
  - `phonetic_group_count = 0.375`
  - `wordplay_group_count = 0.875`
- top-k archetypes:
  - `balanced_mixed = 7`
  - `semantic_heavy = 1`

The top boards are still dominated by narrow variants of the same structure:

- `Gemstones`
- `Planets`
- `Pac-Man ghosts`
- small curated theme swaps
- surface rhyme families such as `Rhymes with -EEL` and `Rhymes with -ASH`
- surface affix families such as `Ends with -AKE`

This is better than raw low-quality noise, but not editorially healthy. The run is still producing local variants of the same machine-friendly formula instead of meaningfully different publishable boards.

## Why Yield Collapsed

Yield collapsed because the first recovery pass mostly corrected ranking and late selection, not upstream family exploration.

The current system already has:

- board-family metadata
- editorial-family metadata
- some family-level penalties
- top-k family caps

But the dominant controls are still too late:

- the composer still trims candidate groups by confidence before run-level family suppression matters
- request-level candidate retention still allows the same theme and surface-wordplay families to monopolize the retained pool
- top-k diversity caps only discover the repetition after the candidate pool is already saturated

In practice, the run spends its budget re-proposing the same family neighborhood across many seeds, then dedupes those variants down to a tiny pool.

## Why Balanced Mixed Is Still Overrepresented

The current policy still over-rewards mixedness as a proxy for editorial strength.

Evidence:

- current style target bands still treat `unique_group_type_count = 2-4` as preferred
- current style target bands still expect `wordplay_group_count = 1-2`
- current composer still grants a diversity bonus for `>= 3` unique types
- current scorer still gives a mixed-mechanism bonus whenever the board is not too obviously formulaic
- current archetype classification still labels `>= 3` unique types as `balanced_mixed` by default

That creates a structural prior that says:

- one semantic group is enough
- a theme group is usually welcome
- a lexical or phonetic group usually helps
- variety of mechanism labels is itself style-aligned

That prior is mismatched to the benchmark holdout.

## Why Style Analysis Is Still Miscalibrated

The current style-analysis center is still not the benchmark holdout. It is a local target band system that encodes a mixed-board preference.

Current benchmark comparison from [`benchmark_audit/generated_vs_nyt_comparison.json`](/Users/zoe/ProbFinal/ProbFinalProj/data/processed/final_quality_acceptance/editorial_recovery_run/benchmark_audit/generated_vs_nyt_comparison.json):

- generated `style_alignment_score = 0.8125`
- benchmark holdout `style_alignment_score = 0.5053`
- generated `human_likeness_mean = 0.8125`
- benchmark holdout `human_likeness_mean = 0.5053`
- generated `semantic_group_count = 2.25`
- benchmark holdout `semantic_group_count = 3.7222`
- generated `theme_group_count = 0.875`
- benchmark holdout `theme_group_count = 0.0635`
- generated `wordplay_group_count = 0.875`
- benchmark holdout `wordplay_group_count = 0.2143`
- generated `unique_group_type_count = 2.75`
- benchmark holdout `unique_group_type_count = 1.2778`

This is not a success signal. It means the scoring center is wrong.

The benchmark holdout is mostly semantic-majority:

- board archetypes in the holdout summary:
  - `semantic_heavy = 116`
  - `wordplay_showcase = 7`
  - `balanced_mixed = 3`

The generated top-k is almost the reverse.

## V2 Design

### 1. Move family suppression upstream

Add run-level family accounting that lives across the deterministic batch and affects later requests before the retained pool saturates.

Track at least:

- group family signature
- board family signature
- editorial family signature
- theme family signature
- surface-wordplay family signature
- mechanism-template signature

Apply the accounting in two places:

- group candidate retention inside the composer candidate pool
- board candidate retention inside request-level ranked board selection

Policy shape:

- repeated editorial families get a soft ranking demotion before retention
- repeated microtheme families get stronger demotion and hard caps sooner
- repeated low-payoff lexical and phonetic surface families get stronger demotion and hard caps sooner
- repeated balanced mixed template signatures get capped earlier

Seed diversification should matter as an exploration tiebreak:

- use deterministic seed-derived family tie-breaking among similarly scored candidate families
- prefer under-explored family regions when base quality is otherwise comparable

### 2. Replace balanced-mixed-first with semantic-majority-first

The healthy default board prior becomes:

- `2-3` semantic groups
- `0-1` wordplay groups
- `0-1` theme groups

Consequences:

- balanced mixed remains legal, but no longer gets default preference
- boards with one semantic group plus theme plus phonetic or lexical now need unusually strong editorial payoff to survive
- semantic-majority boards win ties and near-ties
- mixed-board diversity is a conditional bonus, not a primary goal

### 3. Raise the editorial bar for surface wordplay

Do not ban lexical or phonetic wordplay.

Do distinguish:

- surface-only wordplay
- earned wordplay with phrase or clue payoff

V2 policy changes:

- stronger default penalties for naked suffix, prefix, substring, and perfect-rhyme groups
- extra skepticism when surface wordplay co-occurs with a microtheme
- explicit repeated-surface-wordplay penalties across a run
- interpretable score breakdown entries for low-payoff rhyme and low-payoff affix demotion

### 4. Make editorial flatness and family saturation matter more

The current signals are directionally right but under-weighted:

- `editorial_flatness_score`
- `family_saturation`
- `family_repetition_risk`
- `formulaic_mix_score`
- `microtheme_smallness`

V2 will strengthen those signals in:

- composer ranking
- scorer penalties
- top-k family suppression
- borderline downgrade hooks where the board is structurally fine but editorially stale

The strongest demotion path should apply to the dominant bad template:

- exactly one semantic group
- one theme group
- one phonetic group
- four unique mechanism labels
- surface-only payoff

### 5. Re-anchor style analysis to the benchmark center

The style-analysis center must be the benchmark holdout, not a broad mixed-board preference band.

V2 changes:

- update the reference target policy to reflect semantic-majority benchmark reality
- compute style-alignment against benchmark-centered expectations, with extra attention to inflation-prone metrics
- add explicit benchmark-anchor diagnostics and inflation flags
- prevent generated boards from scoring as more NYT-like than the holdout simply because they check more mechanism boxes

### 6. Keep solver disagreement diagnostic-only

No change in philosophy:

- solver disagreement stays visible
- solver disagreement remains a warning or tie-break context only
- solver disagreement must not materially drive publishability ranking

The v2 work will audit the current path and keep it that way.

## Files Expected To Change

Primary implementation targets:

- [`backend/app/pipeline/builder.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/pipeline/builder.py)
- [`backend/app/services/final_quality_acceptance_service.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/services/final_quality_acceptance_service.py)
- [`backend/app/services/generation_service.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/services/generation_service.py)
- [`backend/app/scoring/human_scoring_strategy.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/scoring/human_scoring_strategy.py)
- [`backend/app/scoring/style_analysis.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/scoring/style_analysis.py)
- [`backend/app/scoring/calibration.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/scoring/calibration.py)
- [`backend/app/scoring/funnel_report.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/scoring/funnel_report.py)
- [`backend/app/scoring/benchmark_audit.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/scoring/benchmark_audit.py)
- [`backend/app/core/stage2_composer_policy.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/core/stage2_composer_policy.py)
- [`backend/app/core/stage3_style_policy.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/core/stage3_style_policy.py)
- [`backend/app/core/editorial_quality.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/core/editorial_quality.py)
- [`backend/app/core/policy_snapshot.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/core/policy_snapshot.py)
- [`backend/app/schemas/evaluation_models.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/schemas/evaluation_models.py)
- [`backend/app/schemas/benchmark_models.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/app/schemas/benchmark_models.py)
- [`scripts/run_final_quality_acceptance.py`](/Users/zoe/ProbFinal/ProbFinalProj/scripts/run_final_quality_acceptance.py)
- [`scripts/compare_final_quality_runs.py`](/Users/zoe/ProbFinal/ProbFinalProj/scripts/compare_final_quality_runs.py)
- [`backend/tests/test_editorial_quality_recovery.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/tests/test_editorial_quality_recovery.py)
- [`backend/tests/test_stage3_a_plus.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/tests/test_stage3_a_plus.py)
- [`backend/tests/test_final_quality_acceptance.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/tests/test_final_quality_acceptance.py)
- [`backend/tests/test_stage1_quality_control.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/tests/test_stage1_quality_control.py)
- [`backend/tests/test_nyt_benchmark_audit.py`](/Users/zoe/ProbFinal/ProbFinalProj/backend/tests/test_nyt_benchmark_audit.py)

Reference policy target update:

- [`data/reference/style_targets_v1.json`](/Users/zoe/ProbFinal/ProbFinalProj/data/reference/style_targets_v1.json) or a versioned successor if a clean target bump is clearer

## TDD Implementation Plan

### Phase A

- write the audit note in this file
- capture the current failure mode numerically
- keep the scope bounded to policy correction, upstream suppression, and calibration

### Phase B

- add failing tests for upstream family suppression and per-run caps
- implement shared run-level family accounting across deterministic batch requests
- push family suppression into candidate generation and request-level candidate retention
- emit run-level family diagnostics into persisted artifacts

### Phase C

- add failing tests for semantic-majority preference over formulaic balanced mixed boards
- revise composer scoring and retention to prefer semantic-majority defaults
- add semantic-majority and balanced-mixed rate outputs

### Phase D

- add failing tests for surface-only wordplay demotion and microtheme-plus-wordplay penalties
- strengthen scorer and style-analysis penalties
- keep the score breakdown human-readable

### Phase E

- add failing tests for benchmark-centered style calibration and inflation warnings
- update target bands and style-alignment computation
- extend benchmark audit outputs with inflation diagnostics

### Phase F

- rerun the deterministic `200` request batch on the same lane
- compare before vs after
- regenerate blind review and solve-playtest packets only if the candidate pool is now healthy enough
- explicitly report any remaining shortfall instead of papering over it

## Intentionally Unchanged

This pass deliberately does not change:

- the Stage 0-4 pipeline contract
- generator family inventory
- external datasets
- benchmark split integrity
- blind review answer hiding
- solve-playtest scoring rules
- the React/FastAPI application structure

## Success Criteria For This Pass

The pass is successful only if the rerun shows both better editorial shape and better breadth:

- more unique boards
- more unique editorial families
- lower family concentration
- lower surface-wordplay and microtheme overrepresentation
- higher semantic-majority share
- lower balanced-mixed default share
- less style inflation against the benchmark holdout
- a top-k that is no longer mostly small variants of the same mixed template
