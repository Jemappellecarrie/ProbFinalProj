# Analysis Bundle For External Review

This bundle is a compact snapshot of the current quality-analysis artifacts for the Connections Puzzle Generator. It is meant to support external review of the generated boards, the yield funnel, the blind-review packet, and the solve-playtest materials without requiring a full repo walk.

The primary run represented here is `data/processed/final_quality_acceptance/post_calibration_run`, created on `2026-03-26T14:42:32.345540Z`. Comparison artifacts are also included from `data/processed/final_quality_acceptance/reports`.

## Folder Guide

- `01_run_summary/`: run config, seed policy, policy snapshot, and a pre-calibration summary for comparison.
- `02_topk_and_candidates/`: current post-calibration top-k boards, accepted/borderline board exports, and a reviewer-oriented sample from the much larger candidate pool.
- `03_funnel_and_audit/`: funnel report, audit outputs, calibration summaries, and before/after comparison artifacts.
- `04_blind_review/`: blind-review packet, instructions, reviewer template, and current scoring/gate-status artifacts.
- `05_solve_playtest/`: solve-playtest packet, instructions, logging template, and current results summary.
- `06_reference_context/`: a small set of docs that explain how to interpret the artifacts.
- `07_missing_or_optional_notes/`: notes about omitted large files and artifact provenance details.

## Review First

1. Start with `03_funnel_and_audit/funnel_report.md` and `03_funnel_and_audit/quality_audit_report.md`.
2. Then inspect `02_topk_and_candidates/top_k.json`, plus `accepted.json` and `borderline.json`.
3. Then do a first-pass blind analysis from `04_blind_review/` without opening the hidden answer key.
4. Then inspect `05_solve_playtest/`.
5. Only after the first-pass blind review, consult `04_blind_review/HIDDEN_answer_key/blind_review_key.json` if needed.

## Blind-Review Warning

The blind-review answer key is intentionally hidden in `04_blind_review/HIDDEN_answer_key/`. Do not consult it during the initial blind analysis.

The solve-playtest key is likewise hidden in `05_solve_playtest/HIDDEN_answer_key/`.

## Current Known Status

- The evaluation and review-prep pipeline is in place, and the bundle includes the current post-calibration run artifacts plus human-review materials.
- The post-calibration run shows a broader persisted pool than the earlier narrow-yield evidence, but the funnel still collapses hard at selection: `unique_board_count = 30`, `top_k_unique_count = 20`, and `selected_unique_board_count = 1`.
- The current audit still shows all generated top-k boards as `accepted_borderline`, with `0` `accepted_high_confidence` boards and a machine publishable proxy of `0.0`.
- The formal human 40% publishable gate remains unresolved until real blind-review forms are completed and scored.

## Important Provenance Note

The primary run files in this bundle come from `post_calibration_run`. The stored before/after calibration comparison artifacts in `03_funnel_and_audit/` are copied as-is from the repo and currently reference `sanity_post2` as the comparison after-run. See `07_missing_or_optional_notes/comparison_context_note.md` for that nuance.
