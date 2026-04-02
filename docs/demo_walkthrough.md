# Demo Walkthrough

## Goal

This walkthrough is the shortest reliable demo path for a grader or teammate.

## Setup

```bash
cp .env.example .env
make bootstrap
```

## Live Demo Steps

1. Start the backend.

```bash
make backend-dev
```

2. Start the frontend in a second terminal.

```bash
make frontend-dev
```

3. Open [http://localhost:5173](http://localhost:5173).

4. Use `Load Static Sample` first to confirm the UI and API contract load.

5. Use `Generate Puzzle` to request a fresh board.

6. Use `Reveal Answers` to show the four groups and their mechanism types.

7. In developer mode, point out:
   - verifier decision
   - mechanism mix
   - score breakdown
   - style-analysis summary
   - raw trace payload

8. Run a batch evaluation in a terminal.

```bash
CONNECTIONS_DEMO_MODE=false \
backend/.venv/bin/python scripts/evaluate_batch.py \
  --num-puzzles 5 \
  --top-k 3 \
  --output-dir data/processed/eval_runs/demo_walkthrough_run \
  --no-demo-mode
```

9. Build the release summary for that run.

```bash
backend/.venv/bin/python scripts/build_release_summary.py \
  --run-dir data/processed/eval_runs/demo_walkthrough_run
```

10. Refresh the frontend debug view and show the latest batch comparison and top-k panel.

## Demo Talking Points

- The backend and frontend are local and reproducible from a fresh checkout.
- The generator supports semantic, lexical, phonetic, and curated-theme groups.
- Verification is not binary only; it exposes `accept`, `borderline`, and `reject`.
- Style and calibration outputs are explicit artifacts, not hidden tuning.
- The project is honest about what is still heuristic or human-owned.
