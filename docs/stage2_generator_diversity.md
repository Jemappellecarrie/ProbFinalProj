# Stage 2 Generator Diversity Upgrade

## Scope

Stage 2 adds the first real non-semantic candidate sources to the existing
Stage 0 semantic baseline and Stage 1 quality-control core. The goal is
controlled board diversity, not maximal novelty: lexical and theme groups must
stay explicit, deterministic, and easy to inspect in traces and evaluation
artifacts.

## Planned Files

- `backend/app/generators/lexical.py`
- `backend/app/generators/theme.py`
- `backend/app/pipeline/builder.py`
- `backend/app/pipeline/semantic_pipeline.py`
- `backend/app/pipeline/orchestration.py`
- `backend/app/services/evaluation_service.py`
- `backend/app/schemas/evaluation_models.py`
- `backend/tests/*` for lexical, theme, composer, pipeline, and evaluation coverage
- `README.md`
- `docs/architecture.md`
- `docs/data_schema.md`
- `docs/human_owned_components.md`

## Lexical Mechanisms

Stage 2 lexical generation is intentionally narrow and high-precision. The
first implemented mechanisms are:

- shared prefix groups from explicit normalized affixes
- shared suffix groups from explicit normalized affixes
- optional repeated-letter or orthographic-pattern groups only when the rule is
  exact, inspectable, and support is clean

Weak same-letter buckets, broad length buckets, and opaque pattern guesses stay
out of scope.

## Theme Mechanisms

Stage 2 theme generation uses a small curated inventory with explicit
membership, labels, and provenance. The first supported theme packs are limited
to compact, inspectable sets already represented in the seed inventory, such as
canonical trivia/theme families and tightly curated named sets.

This is a deterministic lookup layer, not an open-ended retrieval system.

## Composer Mixing Policy

The composer will keep structural validity first and treat diversity as a soft
preference:

- consider semantic, lexical, and theme candidates in the same candidate pool
- allow semantic-only fallback when mixed boards are weaker
- reward strong cross-type mixes with explicit, traceable bonuses
- penalize redundant mechanism usage and cross-type near-duplicates
- keep Stage 1 ambiguity, verification, and scoring as the final accept/reject
  and ranking authority

## Deferred To Stage 3+

Still intentionally deferred:

- phonetic generator as a real mainline source
- style or historical calibration workflows
- broad editorial or NYT-likeness modeling
- overlap-first or false-group generation architectures
- unbounded trivia/theme knowledge expansion
- any claim that final puzzle diversity or ranking is solved
