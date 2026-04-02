# AI Usage

## Scope Of This Document

This document records the AI usage that is directly verifiable from the current
repository worktree and the Stage 4 hardening pass completed in this checkout.

If any teammate used additional AI tools outside the tracked repository changes,
append those details before final submission. This document does not invent or
guess at unverified prior usage.

## Tool Used

- Codex / GPT-5 class coding assistant in a shared local workspace

## How AI Was Used In Stage 4

### Planning and audit

- audited the repository structure, docs, tests, scripts, and frontend/debug
  surfaces
- identified release-hardening gaps for reproducibility, CI, evaluation docs,
  and submission readiness
- drafted `docs/stage4_release_hardening.md`

### Test and regression work

- created the Stage 4 regression fixture pack under
  `backend/tests/fixtures/`
- added release-hardening regression and tooling tests in
  `backend/tests/test_release_hardening.py`
- added evaluation artifact contract assertions

### Tooling and workflow

- added `scripts/build_release_summary.py`
- added `scripts/release_check.py`
- updated `scripts/evaluate_batch.py`
- updated `Makefile`
- added `.github/workflows/ci.yml`

### Frontend and developer UX

- updated frontend type definitions in `frontend/src/types/puzzle.ts`
- revised debug, top-k, and score panel copy and summaries
- fixed the frontend build/typecheck path for the current repository

### Documentation

- rewrote `README.md` for fresh-checkout usability
- added evaluation, demo, release-validation, submission-checklist, and AI-usage docs
- aligned architecture and schema docs with the current Stage 3 plus Stage 4 code

## What AI Produced

AI assistance produced drafts or implementations for:

- code changes
- tests and fixtures
- command and workflow scripts
- CI configuration
- documentation text
- debug/UI wording changes

## Human Responsibilities

Humans remain responsible for:

- deciding project scope and what counts as acceptable submission quality
- reviewing all code and docs before submission
- validating the repository with lint, tests, builds, and release checks
- determining whether heuristic outputs are described honestly
- updating this document if other AI assistance was used elsewhere

## Review And Verification Performed

During this Stage 4 pass, AI-authored changes were followed by:

- targeted pytest runs for the new release-hardening suite
- frontend build validation
- Ruff lint and format checks on changed Python files
- end-to-end batch-evaluation smoke runs

## Explicit Non-Claims

- AI assistance does not imply that puzzle quality is editorially solved.
- AI assistance does not replace human review of heuristics, thresholds, style
  targets, or final submission claims.
- This document is exhaustive for the verified Stage 4 AI-assisted work in this
  checkout, not for unverified external activity.
