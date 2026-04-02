# Data Schema

## `WordEntry`

Canonical seed word record.

- `word_id`: stable identifier
- `surface_form`: display form
- `normalized`: normalized storage form
- `source`: provenance label such as `seed`
- `lemma`: optional normalized lemma
- `notes`: freeform notes
- `known_group_hints`: demo-mode grouping buckets
- `metadata`: extensible source metadata

## `WordFeatures`

Feature bundle produced by the feature extraction layer.

- `word_id`
- `normalized`
- `semantic_tags`
- `lexical_signals`
- `phonetic_signals`
- `theme_tags`
- `extraction_mode`
- `feature_version`
- `provenance`
- `debug_attributes`

## `GroupCandidate`

Candidate four-word group.

- `candidate_id`
- `group_type`
- `label`
- `rationale`
- `words`
- `word_ids`
- `source_strategy`
- `extraction_mode`
- `confidence`
- `metadata`

Generator-specific `metadata` now carries the Stage 0-2 evidence bundles rather
than changing the outer contract. Examples include:

- semantic: `rule_signature`, `shared_tags`, centroid/member evidence
- lexical: `pattern_type`, `normalized_pattern`, matched lexical feature
  evidence, rule signature
- phonetic: `phonetic_pattern_type`, `normalized_phonetic_signature`,
  pronunciation membership evidence, rule signature
- theme: `theme_name`, `theme_source`, curated membership evidence, rule
  signature

## `PuzzleCandidate`

Composed puzzle candidate.

- `puzzle_id`
- `board_words`
- `groups`
- `compatibility_notes`
- `metadata`

`metadata` now also carries additive composer/debug fields such as:

- `mixed_board`
- `mechanism_mix_summary`
- `mechanism_mix_signature`
- `unique_group_type_count`
- `ranking_score`
- `composition_trace`

## `SolverResult`

Raw solver/verifier adapter output.

- `backend_name`
- `solved`
- `proposed_groups`
- `alternative_groupings_detected`
- `notes`
- `raw_output`

## `VerificationResult`

Verifier summary and rejection diagnostics.

- `passed`
- `decision`
- `reject_reasons`
- `warning_flags`
- `leakage_estimate`
- `ambiguity_score`
- `summary_metrics`
- `evidence_refs`
- `notes`
- `metadata`

## `PuzzleScore`

Ranking metadata.

- `scorer_name`
- `overall`
- `coherence`
- `ambiguity_penalty`
- `human_likeness`
- `style_analysis`
- `components`
- `notes`

## `GenerationTrace`

Developer-mode trace for reproducibility and debugging.

- `trace_id`
- `request_id`
- `mode`
- `feature_extractor`
- `generators`
- `solver_backend`
- `scorer`
- `events`
- `ensemble_result`
- `ambiguity_report`
- `style_analysis`
- `metadata`

## `AmbiguityReport`

Structured ambiguity scaffold output.

- `evaluator_name`
- `risk_level`
- `penalty_hint`
- `reject_recommended`
- `summary`
- `evidence`
- `notes`
- `metadata`

`evidence` now includes Stage 1 board-analysis detail such as:

- `group_coherence_summaries`
- `word_fit_summaries`
- `word_group_leakage`
- `cross_group_compatibility`
- `alternative_groupings`
- `board_summary`

## `EnsembleSolverResult`

Aggregate solver ensemble output.

- `coordinator_name`
- `primary_solver_name`
- `votes`
- `agreement_summary`
- `notes`
- `metadata`

## `StyleAnalysisReport`

Interpretable Stage 3 style-analysis output.

- `analyzer_name`
- `archetype`
- `nyt_likeness`
- `signals`
- `group_style_summaries`
- `board_style_summary`
- `mechanism_mix_profile`
- `style_target_comparison`
- `out_of_band_flags`
- `notes`
- `metadata`

## `BatchEvaluationSummary`

Top-level offline evaluation summary.

- `run_id`
- `created_at`
- `total_generated`
- `accepted_count`
- `rejected_count`
- `acceptance_rate`
- `reject_reason_histogram`
- `generator_mix`
- `score_distribution`
- `ambiguity_risk_distribution`
- `solver_agreement_statistics`
- `top_k`
- `calibration_summary`
- `output_dir`
- `notes`

`generator_mix` now includes both per-group counts and per-board mix summaries,
including:

- `board_mix_counts`
- `board_type_signature_counts`

`calibration_summary` now carries Stage 3 offline review artifacts such as:

- accepted / rejected / top-k mechanism-mix and style aggregates
- target-band comparisons against `data/reference/style_targets_v1.json`
- threshold diagnostics for out-of-band mechanism or style drift

Accepted, rejected, and ranked puzzle records now also preserve grouped
solution word sets in addition to board-level word order and labels. This keeps
the persisted artifact bundle sufficient for blind review packet generation
without rerunning generation.

## Persisted Evaluation Files

The evaluation workflow now relies on a stable file bundle rather than a single
summary:

- `summary.json`
- `accepted.json`
- `rejected.json`
- `top_k.json`
- `calibration_summary.json`
- `style_summary.json`
- `mechanism_mix_summary.json`
- `threshold_diagnostics.json`
- optional `traces.json`
- Stage 4 `release_summary.json`
- Stage 4 `release_summary.md`

These files are written under `data/processed/eval_runs/<run_id>/`.

## Public Benchmark Artifacts

The external benchmark audit writes a second local artifact family under
`data/external/nyt_connections_public/`.

### Normalized benchmark boards

- `boards_v1.jsonl`
- `boards_v1.parquet`
- `benchmark_manifest.json`

Each normalized board record includes:

- `benchmark_board_id`
- `source_dataset`
- `source_provenance`
- `source_game_id`
- `puzzle_date`
- `board_words`
- `groups`
- `board_signature`
- `solution_signature`

### Split manifests

- `calibration_split.json`
- `holdout_split.json`
- optional `freshness_split.json`

### Audit and review outputs

- `nyt_benchmark_summary.json`
- `generated_vs_nyt_comparison.json`
- `quality_audit_report.json`
- `quality_audit_report.md`
- `blind_review_packet.json`
- `blind_review_packet.csv`
- `blind_review_key.json`
- `blind_review_results.json`
- `blind_review_results.md`
- `final_quality_gate.json`
