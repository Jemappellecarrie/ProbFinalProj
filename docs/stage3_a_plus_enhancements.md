# Stage 3 A+ Enhancements

## Scope

Stage 3 adds a narrow A+ layer on top of the existing Stage 0 semantic
hardening, Stage 1 quality-control core, and Stage 2 generator diversity work.
The goal is not to solve editorial quality. The goal is to add:

- reproducible batch-calibration summaries from existing evaluation artifacts
- a small, high-precision phonetic / wordplay generator
- a real, interpretable style-analysis feature layer
- additive ranking and verifier improvements informed by calibration evidence

Stage 3 stays within the current FastAPI service flow, typed schemas, trace
payloads, batch-evaluation persistence, and deterministic ranking contracts.

## Files Changed

Primary implementation files:

- `backend/app/generators/phonetic.py`
- `backend/app/scoring/style_analysis.py`
- `backend/app/scoring/human_scoring_strategy.py`
- `backend/app/solver/verifier.py`
- `backend/app/services/evaluation_service.py`
- `backend/app/schemas/evaluation_models.py`
- `backend/app/schemas/puzzle_models.py`
- `backend/app/pipeline/semantic_pipeline.py`
- `backend/app/pipeline/orchestration.py`
- `backend/app/pipeline/builder.py`
- `scripts/evaluate_batch.py`

Additive helpers / fixtures:

- `backend/app/core/stage3_style_policy.py`
- `backend/app/scoring/calibration.py`
- `data/reference/style_targets_v1.json`
- `backend/tests/test_stage3_a_plus.py`
- updates to existing pipeline, schema, and evaluation tests

## Calibration Workflow

Stage 3 calibration is an offline feedback loop, not a hidden optimizer.

1. Run `scripts/evaluate_batch.py` against the current pipeline.
2. Aggregate accepted, rejected, and top-k records into stable summaries for:
   mechanism mix, ambiguity pressure, scoring components, label/rule shape,
   diversity, and style-analysis outputs.
3. Compare those summaries against local versioned target bands in
   `data/reference/style_targets_v1.json`.
4. Persist machine-readable calibration artifacts alongside each eval run so
   threshold review is evidence-backed and reproducible.
5. Use those outputs to tune additive ranking and borderline-policy hooks while
   keeping Stage 1 structural quality dominant.

Implemented artifact files:

- `calibration_summary.json`
- `style_summary.json`
- `mechanism_mix_summary.json`
- `threshold_diagnostics.json`

## Phonetic Mechanisms

Stage 3 phonetic generation stays intentionally narrow and evidence-rich. First
wave mechanisms:

- perfect rhyme groups from explicit pronunciation families
- exact homophone classes when the evidence is local and unambiguous

Current Stage 3 deliberately stops there. Matching stressed endings beyond
those exact mechanisms remain deferred so the generator stays small and high
precision.

All phonetic candidates must expose deterministic signatures, normalized rule
metadata, per-word membership evidence, and a concise rationale explaining the
mechanism.

## Style-Analysis Signals

Stage 3 style analysis becomes a decomposed feature layer with interpretable
signals rather than a placeholder scalar.

Group-level signals:

- mechanism family and archetype
- label clarity / specificity
- evidence interpretability
- wordplay presence and strength
- redundancy or novelty warnings

Board-level signals:

- mechanism-mix profile
- semantic versus wordplay balance
- archetype diversity
- label-shape consistency
- monotony / redundancy indicators
- coherence versus trickiness balance

Calibration-aware outputs:

- within-band versus out-of-band comparisons
- mechanism overrepresentation / underrepresentation flags
- style-drift notes against local target bands

Current ranking / verifier integration:

- scorer adds small style-alignment, wordplay, and phonetic-showcase bonuses
- scorer adds monotony, out-of-band, and decision-class penalties
- verifier emits style warnings and can conservatively demote strongly monotone
  single-mechanism boards to `borderline`
- structural rejects and ambiguity pressure remain dominant over style

## Deferred Beyond Stage 3

Still intentionally deferred:

- broad or noisy phonetic coverage
- hidden-download pronunciation systems or runtime web fetches
- black-box NYT-likeness modeling
- large historical corpus scraping
- replacing Stage 1 ambiguity / verifier policy as the primary gate
- any claim that editorial ranking, style, or puzzle quality is solved
