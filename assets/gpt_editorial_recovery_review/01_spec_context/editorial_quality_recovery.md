# Editorial Quality Recovery

## Current Failure Mode

The current system is not failing to produce boards. It is failing to surface the right ones.

Observed post-calibration top-k behavior:

- top-k is dominated by repeated `semantic + lexical + phonetic + theme` boards
- repeated labels and microfamilies such as `Gemstones`, `Planets`, `Pac-Man ghosts`, `Ends with -AKE`, and `Rhymes with -ASH` are heavily overrepresented
- board-level dedupe is active, but family-level repetition still reaches top-k because different word boards keep expressing the same editorial family
- current top-ranked boards look mechanically balanced more often than they look curated or publishable

## Family-Repetition Diagnosis

The ranking lane currently dedupes by board signature only. That misses repeated editorial families such as:

- the same semantic/theme pack reused across many boards
- the same suffix/rhyme family reused across many boards
- the same balanced-mixed mechanism template reused with only small substitutions

This means top-k quality can look narrow even when exact board words are different.

## Ranking Bonus Misalignment

Current incentives are too presence-based:

- composer ranking adds diversity bonuses for lexical, phonetic, and theme presence
- scorer adds unconditional `style_alignment_bonus`, `wordplay_bonus`, `phonetic_showcase_bonus`, and `mixed_mechanism_bonus`
- style analysis treats `balanced_mixed` as a favorable archetype too easily
- solver disagreement currently contributes to borderline demotion more strongly than the editorial evidence warrants

As a result, a safe formulaic mixed board can outrank a more editorially satisfying board simply by checking mechanism boxes.

## Proposed Recovery

### 1. Family signatures and diversity control

Add deterministic additive metadata for:

- group family signature
- board family signature
- editorial family signature

Use those signatures to add:

- family repetition penalties
- top-k family caps
- repeated microtheme suppression
- repeated surface-wordplay suppression

Board-level dedupe stays in place, but family-level diversity becomes a stronger editorial filter.

### 2. Conditional bonuses instead of presence bonuses

Rework the ranking policy so:

- mixed-mechanism bonuses only apply when the board is not formulaic
- wordplay bonuses require editorial payoff, not just naked pattern/rhyme presence
- phonetic bonuses require stronger phonetic evidence and low family repetition
- style alignment cannot outweigh editorial flatness

Add explicit penalties for:

- formulaic mix
- family repetition
- repeated pattern families
- repeated small curated themes
- overly surface-only wordplay
- editorial flatness

### 3. Editorial verifier/style layer

Add additive editorial warning and penalty signals such as:

- `too_formulaic`
- `family_repetition`
- `overly_surface_wordplay`
- `editorial_flatness`
- `microtheme_trivia_smallness`
- `weak_label_naturalness`

These are primarily ranking and borderline-demotion signals, not blanket reject rules.

### 4. Solver disagreement downgrade

Keep solver disagreement visible in artifacts, but reduce its influence so it acts as:

- diagnostics
- a low-weight warning
- supporting context only

It should not behave like a strong publishability proxy.

## What Will Change

- Stage 2 composer metadata and ranking signals
- final-quality top-k selection and family diversity control
- style-analysis metrics and out-of-band/editorial flags
- verifier warning/demotion hooks for editorial flatness and formulaic repetition
- scorer bonus/penalty balance
- funnel and evaluation artifacts with family-level concentration summaries

## What Will Stay Untouched

- generator families and external data scope
- Stage 0–4 architecture
- benchmark holdout integrity
- blind-review source hiding and scoring logic
- structural ambiguity analysis as the main correctness backbone

## Intended Outcome

Top-k should become less dominated by repeated balanced-mixed templates and more likely to surface boards with real editorial payoff, even if that means fewer flashy lexical/phonetic/theme groups survive ranking.
