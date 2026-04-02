# Editorial Polish V4

## Context

Editorial polish v3 made the offline pool reviewable, but it did not finish the winner path. The system now produces enough distinct top-k boards for blind review, yet the default selected board per request still leans too hard toward repeated mixed or microtheme-heavy shapes. This pass is the final narrow polish before human blind review and solve-playtest scoring.

## Current Winner-Path Diagnosis

- `selected_unique_board_count` improved to `14`, so the system is no longer fully single-board collapsed.
- `selected_unique_family_count` improved to `43`, which means winner selection is exploring more editorial families than before.
- But `winner_family_repetition_rate` is still `1.0`, which means every winning family is still repeating somewhere in the run.
- Request-level selection is therefore only partially fixed: it prefers fresh families early, but once the run moves past the first layer of novelty, the live winner path still settles back into a narrow set of repeated shapes.

## Why Semantic-Majority Is Still Too Weak

- `semantic_majority_board_rate` fell to `0.2932`, which moved away from the benchmark center rather than toward it.
- Winner slices still admit too many mixed boards with insufficient semantic mass, especially when a local score edge comes from surface mechanism presence.
- Composer caps are currently strict enough to defer many repeated families, but deferred backfill then reintroduces too many mixed boards without enough semantic-majority pressure.
- Winner tie-break behavior still does not treat semantic-majority as the default strong board shape.

## Why Surface Wordplay Is Still Too Dominant

- `surface_wordplay_board_rate` increased to `0.5708`.
- `microtheme_plus_wordplay_cooccurrence_rate` increased to `0.4473`.
- Benchmark audit still flags too much lexical/phonetic surface patterning and too much formulaic mechanism mixing.
- Current scoring does distinguish surface wordplay from phrase or clue payoff, but the demotion is still too soft once these boards survive into the winner-path candidate slice.

## Where Microtheme Overuse Still Enters

- `repeated_theme_family_count` remains elevated.
- Small curated themes are tracked and capped, but the current composer flow over-relies on deferred backfill after hard family skips.
- That means microtheme families can still re-enter the request-level retained set even when they have already saturated the run.
- The same narrow safe packs then remain visible in both candidate retention and final winner choice.

## Label / Clue Polish Plan

- Keep label polish deterministic and conservative.
- Improve obvious surface-pattern labels so they read more like concise clue headings and less like generator taxonomy.
- Prefer short frame-style labels when the evidence directly supports them.
- Do not invent unsupported clue phrasing or free-form editorial rewrite.
- Expose label diagnostics more clearly so reviewer-side analysis can see whether polish actually reduced taxonomy-like phrasing.

## Exact Changes In Scope

### 1. Winner-path recovery

- Strengthen request-level winner suppression using both run-wide counts and recent-winner history.
- Make winner tie-breaks care more about family spread, semantic-majority shape, and repeated microtheme or surface-wordplay reuse.
- Persist clearer winner diagnostics, including winner-only surface-wordplay and semantic-center summaries.

### 2. Stronger semantic-majority / mixed-board policy

- Push composer, scorer, and final top-k ranking further toward `2-3 semantic` as the default healthy prior.
- Demote low-semantic boards that pair microtheme plus surface wordplay.
- Reduce the chance that balanced mixed or near-balanced mixed boards win by default when semantic-majority alternatives are acceptable.

### 3. Stronger surface-wordplay and microtheme suppression

- Increase penalties for naked suffix, rhyme, and orthographic pattern groups unless clue or phrase payoff is clearly stronger.
- Increase co-occurrence penalties for microtheme plus surface wordplay.
- Make repeated small-theme reuse matter more in winner-path selection and deferred candidate backfill.

### 4. Conservative label and clue polish

- Replace the most taxonomy-like lexical and phonetic labels with shorter frame-style labels where the pattern evidence is explicit.
- Improve clue-like versus taxonomy-like diagnostics without adding any generative rewriting stage.
- Keep label changes narrow enough that artifact compatibility and deterministic behavior remain intact.

### 5. Reporting and comparison updates

- Extend funnel reporting with winner-path metrics that directly expose whether the selected boards are still too surface-heavy or too far from semantic-majority.
- Extend before/after run comparison so v4 explicitly reports winner-path realism, not just pool breadth.

## Intentionally Unchanged

- No new generators
- No new datasets
- No broad architecture rewrite
- No benchmark contamination from blind-review answers
- No opaque scoring model or unrestricted LLM label rewriting
- No change to Stage 0-4 contracts or existing artifact structure beyond additive diagnostics

## Success Criteria For This Pass

- selected winners diversify further instead of settling back into a small repeated family set
- semantic-majority rises rather than falls
- surface wordplay and microtheme-plus-wordplay rates move down
- repeated small-theme families are harder to reuse in the live winner path
- labels become measurably less taxonomy-like and more clue-like
- benchmark deltas move toward the holdout center without reopening the broader modeling roadmap
