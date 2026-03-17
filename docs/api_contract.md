# API Contract

Base path: `/api/v1`

## `GET /health`

Returns service status and mode information.

Response shape:

```json
{
  "status": "ok",
  "app_name": "Connections Puzzle Generator",
  "environment": "development",
  "demo_mode": true
}
```

## `GET /debug/config`

Returns a safe subset of runtime config for local development.

## `GET /metadata/group-types`

Returns supported generator family metadata:

- `semantic`
- `lexical`
- `phonetic`
- `theme`

## `GET /puzzles/sample`

Returns a static sample payload bundled with the repository. Useful for UI bootstrapping and API shape testing.

## `POST /puzzles/generate`

Runs the generation pipeline and returns a generated payload.

Request:

```json
{
  "seed": 17,
  "include_trace": true,
  "developer_mode": true,
  "requested_group_types": ["semantic", "lexical", "phonetic", "theme"]
}
```

Response:

```json
{
  "demo_mode": true,
  "selected_components": {
    "feature_extractor": "mock_word_feature_extractor",
    "generators": [
      "mock_semantic_group_generator",
      "mock_lexical_group_generator",
      "mock_phonetic_group_generator",
      "mock_theme_group_generator"
    ],
    "composer": "baseline_puzzle_composer",
    "solver": "mock_solver_backend",
    "verifier": "baseline_puzzle_verifier",
    "scorer": "mock_puzzle_scorer"
  },
  "warnings": [],
  "puzzle": {},
  "verification": {},
  "score": {},
  "trace": {}
}
```

## Notes

- The current response contract is stable for demo mode.
- Future human-owned implementations should preserve these top-level shapes even if the internals become richer.
