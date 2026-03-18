"""Batch evaluation service tests."""

from __future__ import annotations

import json

from app.config.settings import Settings
from app.schemas.evaluation_models import BatchEvaluationConfig
from app.services.evaluation_service import EvaluationService


def test_batch_evaluation_writes_expected_artifacts(tmp_path) -> None:
    service = EvaluationService(Settings())
    output_dir = tmp_path / "eval_run"
    run = service.evaluate_batch(
        BatchEvaluationConfig(
            num_puzzles=4,
            output_dir=str(output_dir),
            save_traces=True,
            top_k_size=2,
            base_seed=17,
        )
    )

    assert run.summary.total_generated == 4
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "accepted.json").exists()
    assert (output_dir / "rejected.json").exists()
    assert (output_dir / "top_k.json").exists()

    with (output_dir / "summary.json").open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["top_k"]["requested_k"] == 2


def test_latest_debug_view_reads_recent_artifacts(tmp_path) -> None:
    settings = Settings()
    service = EvaluationService(settings)
    output_dir = tmp_path / "latest_eval"
    service.evaluate_batch(
        BatchEvaluationConfig(
            num_puzzles=3,
            output_dir=str(output_dir),
            save_traces=False,
            top_k_size=2,
            base_seed=20,
        )
    )
    service._settings = type("StubSettings", (), {"eval_runs_dir": tmp_path})()  # type: ignore[assignment]
    latest = service.load_latest_debug_view()
    assert latest is not None
    assert latest.summary.total_generated == 3
