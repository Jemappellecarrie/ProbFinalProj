# Release Candidate Validation

## Recommended One-Command Path

```bash
make release-check
```

This runs the Stage 4 release validation helper and checks:

- Ruff lint
- Ruff format check
- backend pytest
- frontend build
- demo generation smoke
- non-demo batch-evaluation smoke
- release summary generation

The Ruff step is intentionally scoped to the Stage 4-maintained Python paths,
the `scripts/` directory, and the backend test suite so the validation path
stays focused on submission-critical work rather than unrelated legacy lint
debt elsewhere in the repository.

## Step-By-Step Equivalent

```bash
make lint-backend
make format-check-backend
make test-backend
make frontend-build
make demo-generate
make evaluate-batch-smoke
make release-summary
```

## Expected Output Locations

- smoke evaluation artifacts:
  `data/processed/release_validation/make_release_check/`
- release summary bundle:
  `data/processed/release_validation/make_release_check/release_summary.json`
  and
  `data/processed/release_validation/make_release_check/release_summary.md`

## What To Inspect Before Submission

- tests are green
- frontend build succeeds
- `summary.json` exists for the smoke run
- `top_k.json` exists and contains ranked boards
- calibration artifacts exist
- release summary files exist
- no documentation still describes the non-demo path as unimplemented

## Clean-State Note

The validation path is designed for a normal working checkout. It does not
require destructive cleanup commands and should not depend on hidden downloads
or network access at runtime.
