"""Batch evaluation service tests."""

from __future__ import annotations

import json

from app.config.settings import Settings
from app.schemas.api import PuzzleGenerationRequest
from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    AmbiguityEvidence,
    AmbiguityReport,
    AmbiguityRiskLevel,
    BatchEvaluationConfig,
    ScoreBreakdownView,
)
from app.services.evaluation_service import EvaluationService
from app.services.generation_service import GenerationService


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
    assert (output_dir / "calibration_summary.json").exists()
    assert (output_dir / "style_summary.json").exists()
    assert (output_dir / "mechanism_mix_summary.json").exists()
    assert (output_dir / "threshold_diagnostics.json").exists()

    with (output_dir / "summary.json").open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["top_k"]["requested_k"] == 2
    assert summary["calibration_summary"]["target_version"] == "style_targets_v1"


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


def test_semantic_baseline_batch_evaluation_runs_when_mode_matches(tmp_path) -> None:
    settings = Settings(demo_mode=False)
    service = EvaluationService(settings)
    output_dir = tmp_path / "semantic_eval"

    run = service.evaluate_batch(
        BatchEvaluationConfig(
            num_puzzles=2,
            output_dir=str(output_dir),
            save_traces=False,
            top_k_size=1,
            base_seed=11,
            demo_mode=False,
        )
    )

    assert run.summary.total_generated == 2
    assert (output_dir / "summary.json").exists()
    assert run.summary.generator_mix.group_type_counts["semantic"] >= 2
    assert run.summary.generator_mix.group_type_counts["lexical"] >= 1
    assert run.summary.generator_mix.group_type_counts.get("phonetic", 0) >= 0
    assert run.summary.generator_mix.group_type_counts.get("theme", 0) >= 0
    assert run.summary.generator_mix.board_mix_counts["semantic_only"] >= 0
    assert run.summary.top_k.ranked_puzzles[0].mechanism_mix_summary
    assert run.summary.top_k.ranked_puzzles[0].mechanism_mix_summary["semantic"] >= 2
    assert run.summary.top_k.ranked_puzzles[0].style_alignment_score is not None
    assert run.summary.calibration_summary is not None
    assert run.summary.calibration_summary.target_version == "style_targets_v1"

    generation = GenerationService(settings).generate_puzzle(
        PuzzleGenerationRequest(seed=11, include_trace=True)
    )
    assert generation.demo_mode is False
    assert generation.puzzle.metadata["semantic_majority_board"] is True
    assert generation.puzzle.metadata["semantic_group_count"] >= 2
    assert generation.trace is not None
    assert generation.trace.metadata["selection_summary"]["semantic_group_count"] >= 2


def test_top_k_ranking_prefers_accept_over_borderline_even_when_scores_are_close() -> None:
    accept_record = AcceptedPuzzleRecord(
        iteration_index=0,
        request_seed=17,
        puzzle_id="puzzle_accept",
        board_words=[f"A{i}" for i in range(16)],
        group_labels=["A", "B", "C", "D"],
        group_types=["semantic"] * 4,
        verification_decision="accept",
        score_breakdown=ScoreBreakdownView(
            overall=0.81,
            coherence=0.9,
            ambiguity_penalty=0.12,
            components={"group_coherence": 0.9},
        ),
        ambiguity_report=AmbiguityReport(
            evaluator_name="human_ambiguity_evaluator",
            risk_level=AmbiguityRiskLevel.LOW,
            penalty_hint=0.12,
            reject_recommended=False,
            summary="Low ambiguity.",
            evidence=AmbiguityEvidence(triggered_flags=[]),
        ),
    )
    borderline_record = AcceptedPuzzleRecord(
        iteration_index=1,
        request_seed=18,
        puzzle_id="puzzle_borderline",
        board_words=[f"B{i}" for i in range(16)],
        group_labels=["A", "B", "C", "D"],
        group_types=["semantic"] * 4,
        verification_decision="borderline",
        score_breakdown=ScoreBreakdownView(
            overall=0.88,
            coherence=0.92,
            ambiguity_penalty=0.24,
            components={"group_coherence": 0.92},
        ),
        ambiguity_report=AmbiguityReport(
            evaluator_name="human_ambiguity_evaluator",
            risk_level=AmbiguityRiskLevel.MEDIUM,
            penalty_hint=0.24,
            reject_recommended=False,
            summary="Moderate ambiguity.",
            evidence=AmbiguityEvidence(triggered_flags=["moderate_leakage"]),
        ),
    )

    top_k = EvaluationService._rank_top_k([borderline_record, accept_record], top_k_size=2)

    assert top_k.ranked_puzzles[0].puzzle_id == "puzzle_accept"
    assert top_k.ranked_puzzles[1].puzzle_id == "puzzle_borderline"


def test_top_k_ranking_deduplicates_repeated_puzzle_ids() -> None:
    records = []
    for index, score in enumerate((0.91, 0.88, 0.84), start=1):
        records.append(
            AcceptedPuzzleRecord(
                iteration_index=index,
                request_seed=10 + index,
                puzzle_id="repeated_board" if index < 3 else "distinct_board",
                board_words=[f"W{index}_{word}" for word in range(16)],
                group_labels=["A", "B", "C", "D"],
                group_types=["semantic", "lexical", "phonetic", "theme"],
                group_word_sets=[
                    [f"A{index}{member}" for member in range(4)],
                    [f"B{index}{member}" for member in range(4)],
                    [f"C{index}{member}" for member in range(4)],
                    [f"D{index}{member}" for member in range(4)],
                ],
                verification_decision="accept",
                score_breakdown=ScoreBreakdownView(
                    overall=score,
                    coherence=0.9,
                    ambiguity_penalty=0.1,
                    components={"composer_ranking_score": score},
                ),
            )
        )

    top_k = EvaluationService._rank_top_k(records, top_k_size=5)

    assert [record.puzzle_id for record in top_k.ranked_puzzles] == [
        "repeated_board",
        "distinct_board",
    ]


def test_top_k_record_selection_matches_unique_ranked_puzzles() -> None:
    repeated = AcceptedPuzzleRecord(
        iteration_index=0,
        request_seed=17,
        puzzle_id="repeated_board",
        board_words=[f"R{index}" for index in range(16)],
        group_labels=["A", "B", "C", "D"],
        group_word_sets=[
            ["A0", "A1", "A2", "A3"],
            ["B0", "B1", "B2", "B3"],
            ["C0", "C1", "C2", "C3"],
            ["D0", "D1", "D2", "D3"],
        ],
        group_types=["semantic", "lexical", "phonetic", "theme"],
        verification_decision="accept",
        score_breakdown=ScoreBreakdownView(
            overall=0.9,
            coherence=0.9,
            ambiguity_penalty=0.1,
            components={"composer_ranking_score": 1.0},
        ),
    )
    duplicate = repeated.model_copy(update={"iteration_index": 1, "request_seed": 18})
    unique = repeated.model_copy(
        update={
            "puzzle_id": "unique_board",
            "iteration_index": 2,
            "request_seed": 19,
            "board_words": [f"U{index}" for index in range(16)],
        }
    )

    top_k = EvaluationService._rank_top_k([repeated, duplicate, unique], top_k_size=5)
    selected = EvaluationService._select_top_k_records([repeated, duplicate, unique], top_k)

    assert [record.puzzle_id for record in selected] == ["repeated_board", "unique_board"]
