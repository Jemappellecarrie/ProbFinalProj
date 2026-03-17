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

## `PuzzleCandidate`

Composed puzzle candidate.

- `puzzle_id`
- `board_words`
- `groups`
- `compatibility_notes`
- `metadata`

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
- `reject_reasons`
- `leakage_estimate`
- `ambiguity_score`
- `notes`
- `metadata`

## `PuzzleScore`

Ranking metadata.

- `scorer_name`
- `overall`
- `coherence`
- `ambiguity_penalty`
- `human_likeness`
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
- `metadata`
