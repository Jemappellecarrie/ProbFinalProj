# Editorial Polish V3

## Context

Editorial recovery v2 fixed the worst candidate-pool collapse, but the live winner path is still too formulaic. The persisted v2 artifacts show a healthier offline pool and a less brittle top-k, yet the final selected board per request still collapses toward the same repeated family. This pass is a narrow editorial polish on top of the existing Stage 0-4 system and the v2 recovery pass.

## Current Diagnosis

### Winner-path collapse

- `unique_board_count` improved from `8` to `60`, but `selected_unique_board_count` is still `1`.
- Upstream family suppression already affects retained candidates, yet the final winner selection key still mostly resolves on score and local board features.
- As a result, nearby seeds can explore more ideas but still converge on the same winning editorial family.

### Semantic-majority is still too weak

- `semantic_majority_board_rate` is only `0.3543`, still far from the benchmark center.
- Top boards remain overconcentrated in semantic-plus-wordplay shapes such as `3 semantic + 1 lexical` and related mixed templates.
- The current semantic-majority bonus helps, but not enough to redirect winner selection when mixed boards are only slightly higher on local score.

### Surface wordplay is still too dominant

- `surface_wordplay_board_rate` remains `0.4735`.
- `microtheme_plus_wordplay_cooccurrence_rate` remains `0.4298`.
- Generated boards are still benchmark-misaligned on `wordplay_group_count`, `surface_wordplay_score`, and `formulaic_mix_score`.
- The system still treats some suffix/rhyme groups as competitive too often, even when their payoff is mostly pattern presence rather than clue-like satisfaction.

### Microtheme overuse still enters upstream

- `repeated_theme_family_count` increased from `3` to `6`.
- Small curated theme packs are already tracked, but the effective cap is still permissive enough that they keep reappearing across requests and in winner-adjacent slices.
- The same issue then leaks into both top-k composition and final winner selection.

### Labels still read somewhat system-native

- Labels are usually clear, but some lexical and phonetic labels still read like generator metadata instead of editorial clueing.
- The current `label_naturalness_score` is useful but too coarse: it does not distinguish clue-like phrasing from taxonomy-like phrasing, and it does not expose whether any conservative polish was applied.

## Root Cause

The remaining failure is not missing generator breadth. It is policy mismatch:

- winner selection is still insufficiently family-aware
- semantic-majority is still treated as a preference rather than the default shape
- surface wordplay still carries too much weight relative to its editorial payoff
- microtheme families are still allowed to recur too often across a run
- label analysis is scoring clarity more than clue realism

## Changes In Scope

### 1. Winner-path recovery

- Audit and update request-level winner selection in `orchestration.py`.
- Add winner-aware family accounting on the shared run state.
- Penalize repeated winner editorial families, repeated mixed templates, repeated microtheme families, and repeated surface-wordplay winner families before the final winner is chosen.
- Prefer semantic-majority winners when quality is otherwise comparable.
- Persist winner diagnostics so collapse is visible in artifacts, not inferred later.

### 2. Stronger semantic-majority prior

- Increase the semantic-majority bonus and demote balanced mixed boards further in composer and scorer policy.
- Increase penalties for boards with only one semantic group plus microtheme plus surface wordplay.
- Make winner selection explicitly prefer semantic-majority boards over repeated mixed templates when verification class is similar.

### 3. Stronger surface-wordplay and microtheme suppression

- Increase penalties for low-payoff suffix/rhyme/orthographic groups.
- Tighten per-run caps for small microtheme families.
- Add stronger co-occurrence penalties for microtheme plus surface wordplay.
- Promote phrase/template payoff over raw pattern presence where existing metadata supports it.

### 4. Conservative label/clue polish

- Add a deterministic label polish helper for obvious system-like pattern labels.
- Keep the rewrite scope narrow and evidence-backed.
- Add diagnostics for:
  - `label_naturalness_score`
  - `clue_like_label_count`
  - `taxonomy_like_label_count`
  - `label_polish_applied`
- Avoid unsupported label invention.

### 5. Artifact and comparison updates

- Extend funnel reporting with winner-only diversity metrics:
  - `selected_unique_family_count`
  - `winner_family_histogram`
  - `winner_family_repetition_rate`
  - `winner_mechanism_mix_distribution`
  - `semantic_majority_winner_rate`
  - `balanced_mixed_winner_rate`
  - `winner_microtheme_family_count`
  - `microtheme_family_suppression_events`
- Extend before/after comparison output so v3 reporting highlights winner-path behavior, not just offline breadth.

## Intentionally Unchanged

- No new generators
- No new datasets
- No broad scoring rewrite
- No change to Stage 0-4 contracts
- No benchmark contamination from blind-review answers
- No nondeterministic label rewriting or free-form LLM polish

## Success Criteria For This Pass

- selected winners are no longer a single repeated board family
- semantic-majority increases in both the pool and the winner path
- surface wordplay and microtheme co-occurrence decrease
- repeated microtheme families are more tightly capped
- labels become measurably more clue-like and less taxonomy-like
- benchmark deltas move in the right direction without reopening the larger modeling roadmap
