"""Tests for the final quality acceptance sprint workflow."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.config.settings import Settings
from app.core.policy_snapshot import current_policy_snapshot, diff_policy_snapshots
from app.schemas.benchmark_models import QualityGateResult
from app.schemas.evaluation_models import (
    CandidatePoolPuzzleRecord,
    FinalQualityBatchConfig,
    ScoreBreakdownView,
)
from app.scoring.benchmark_audit import normalize_public_benchmark, run_quality_audit
from app.scoring.blind_review import score_blind_review
from app.scoring.final_quality_comparison import build_before_after_funnel_comparison
from app.scoring.funnel_report import build_funnel_report
from app.scoring.solve_playtest import build_solve_playtest_packet, score_solve_playtest
from app.services.final_quality_acceptance_service import FinalQualityAcceptanceService

from .test_blind_review import _write_generated_run
from .test_nyt_benchmark_audit import _write_benchmark_fixture


def _candidate_record(
    *,
    request_seed: int,
    puzzle_id: str,
    board_words: list[str],
    group_labels: list[str],
    group_word_sets: list[list[str]],
    decision: str,
    request_rank: int,
    selected: bool,
    reject_reasons: list[str] | None = None,
) -> CandidatePoolPuzzleRecord:
    return CandidatePoolPuzzleRecord(
        iteration_index=request_seed - 100,
        request_seed=request_seed,
        request_rank=request_rank,
        selected=selected,
        puzzle_id=puzzle_id,
        board_words=board_words,
        group_labels=group_labels,
        group_word_sets=group_word_sets,
        group_types=["semantic", "lexical", "phonetic", "theme"],
        mechanism_mix_summary={"semantic": 1, "lexical": 1, "phonetic": 1, "theme": 1},
        mixed_board=True,
        verification_decision=decision,
        score_breakdown=ScoreBreakdownView(
            overall=0.9 - (request_rank * 0.01),
            coherence=0.85,
            ambiguity_penalty=0.15,
            human_likeness=0.75,
            components={"composer_ranking_score": 0.8 - (request_rank * 0.01)},
        ),
        reject_reasons=reject_reasons or [],
        warnings=["weak_group_support"] if decision == "borderline" else [],
        selected_components={"generators": ["human_semantic_group_generator"]},
        candidate_source="request_candidate_pool",
    )


def test_build_funnel_report_computes_uniqueness_and_duplicate_collapse() -> None:
    candidates = [
        _candidate_record(
            request_seed=100,
            puzzle_id="puzzle_a",
            board_words=[f"A{index}" for index in range(16)],
            group_labels=["Alpha", "Beta", "Gamma", "Delta"],
            group_word_sets=[
                ["A0", "A1", "A2", "A3"],
                ["A4", "A5", "A6", "A7"],
                ["A8", "A9", "A10", "A11"],
                ["A12", "A13", "A14", "A15"],
            ],
            decision="accept",
            request_rank=1,
            selected=True,
        ),
        _candidate_record(
            request_seed=101,
            puzzle_id="puzzle_a_dup",
            board_words=[f"A{index}" for index in range(16)],
            group_labels=["Alpha", "Beta", "Gamma", "Delta"],
            group_word_sets=[
                ["A0", "A1", "A2", "A3"],
                ["A4", "A5", "A6", "A7"],
                ["A8", "A9", "A10", "A11"],
                ["A12", "A13", "A14", "A15"],
            ],
            decision="borderline",
            request_rank=1,
            selected=True,
        ),
        _candidate_record(
            request_seed=102,
            puzzle_id="puzzle_b",
            board_words=[f"B{index}" for index in range(16)],
            group_labels=["Echo", "Foxtrot", "Golf", "Hotel"],
            group_word_sets=[
                ["B0", "B1", "B2", "B3"],
                ["B4", "B5", "B6", "B7"],
                ["B8", "B9", "B10", "B11"],
                ["B12", "B13", "B14", "B15"],
            ],
            decision="reject",
            request_rank=2,
            selected=False,
            reject_reasons=["ambiguous_grouping", "low_coherence"],
        ),
    ]
    request_diagnostics = [
        {
            "request_seed": 100,
            "evaluated_combination_count": 8,
            "rejected_combination_reason_counts": {"overlapping_words": 3},
        },
        {
            "request_seed": 101,
            "evaluated_combination_count": 8,
            "rejected_combination_reason_counts": {"overlapping_words": 2},
        },
    ]

    report = build_funnel_report(
        total_generation_requests=2,
        candidate_records=candidates,
        top_review_candidates=candidates[:2],
        request_diagnostics=request_diagnostics,
    )

    assert report["total_generation_requests"] == 2
    assert report["total_puzzle_candidates_seen"] == 21
    assert report["structurally_valid_count"] == 16
    assert report["structurally_invalid_count"] == 5
    assert report["unique_board_count"] == 2
    assert report["duplicate_board_count"] == 1
    assert report["accepted_count"] == 1
    assert report["borderline_count"] == 1
    assert report["rejected_count"] == 1
    assert report["top_k_unique_count"] == 1
    assert report["reject_reason_breakdown"]["ambiguous_grouping"] == 1
    assert report["warning_flag_breakdown"]["weak_group_support"] == 1
    assert report["duplicate_signature_breakdown"]
    assert report["collapse_diagnostics"]["top_board_signature_share"] == 0.6667


def test_policy_snapshot_diff_serializes_only_changed_knobs() -> None:
    before = current_policy_snapshot()
    after = current_policy_snapshot()
    after["stage2_composer"]["max_ranked_puzzles"] = (
        before["stage2_composer"]["max_ranked_puzzles"] + 5
    )
    after["stage3_verifier"]["monotony_warning_threshold"] = 0.8

    diff = diff_policy_snapshots(before, after)

    assert diff["changed"] is True
    assert diff["changes"]["stage2_composer"]["max_ranked_puzzles"] == {
        "before": before["stage2_composer"]["max_ranked_puzzles"],
        "after": before["stage2_composer"]["max_ranked_puzzles"] + 5,
    }
    assert diff["changes"]["stage3_verifier"]["monotony_warning_threshold"] == {
        "before": before["stage3_verifier"]["monotony_warning_threshold"],
        "after": 0.8,
    }


def test_before_after_funnel_comparison_reports_core_deltas() -> None:
    before = {
        "unique_board_count": 5,
        "unique_family_count": 4,
        "selected_unique_board_count": 1,
        "top_k_unique_count": 1,
        "top_k_unique_family_count": 1,
        "accepted_count": 2,
        "borderline_count": 3,
        "rejected_count": 5,
        "formulaic_board_rate": 0.8,
        "repeated_family_rate": 0.7,
    }
    after = {
        "unique_board_count": 18,
        "unique_family_count": 14,
        "selected_unique_board_count": 2,
        "top_k_unique_count": 12,
        "top_k_unique_family_count": 10,
        "accepted_count": 6,
        "borderline_count": 7,
        "rejected_count": 4,
        "formulaic_board_rate": 0.35,
        "repeated_family_rate": 0.2,
    }

    comparison = build_before_after_funnel_comparison(before, after)

    assert comparison["changed"] is True
    assert comparison["metrics"]["unique_board_count"] == {
        "before": 5,
        "after": 18,
        "delta": 13,
    }
    assert comparison["metrics"]["unique_family_count"]["delta"] == 10
    assert comparison["metrics"]["top_k_unique_count"]["delta"] == 11
    assert comparison["metrics"]["top_k_unique_family_count"]["delta"] == 9


def test_final_quality_acceptance_batch_writes_reproducible_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "acceptance_run"

    run = FinalQualityAcceptanceService(Settings(demo_mode=False)).run_batch(
        FinalQualityBatchConfig(
            num_requests=3,
            output_dir=str(output_dir),
            top_k_size=4,
            base_seed=31,
            candidate_pool_limit=4,
            save_traces=False,
            demo_mode=False,
        )
    )

    assert run.output_files["batch_config"].endswith("batch_config.json")
    assert (output_dir / "batch_config.json").exists()
    assert (output_dir / "seed_manifest.json").exists()
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "candidate_pool.json").exists()
    assert (output_dir / "funnel_report.json").exists()
    assert (output_dir / "funnel_report.md").exists()

    batch_config = json.loads((output_dir / "batch_config.json").read_text())
    seed_manifest = json.loads((output_dir / "seed_manifest.json").read_text())
    funnel_report = json.loads((output_dir / "funnel_report.json").read_text())
    candidate_pool = json.loads((output_dir / "candidate_pool.json").read_text())

    assert batch_config["num_requests"] == 3
    assert seed_manifest["seeds"] == [31, 32, 33]
    assert funnel_report["total_generation_requests"] == 3
    assert funnel_report["top_k_unique_count"] == run.summary.top_k.returned_count
    assert candidate_pool
    assert all("request_rank" in record for record in candidate_pool)


def test_score_blind_review_reports_unresolved_when_no_forms(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    review_dir = tmp_path / "review_packets"
    generated_run_dir = tmp_path / "generated"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    _write_generated_run(generated_run_dir)

    from app.scoring.blind_review import build_blind_review_packet

    build_blind_review_packet(
        run_dir=generated_run_dir,
        normalized_dir=normalized_dir,
        output_dir=review_dir,
        generated_count=1,
        benchmark_count=1,
        seed=23,
    )

    summary = score_blind_review(
        answer_key_path=review_dir / "blind_review_key.json",
        review_paths=[],
        output_dir=review_dir,
    )

    assert isinstance(summary.final_quality_gate, QualityGateResult)
    assert summary.final_quality_gate.resolved is False
    assert summary.final_quality_gate.passed is None
    assert summary.final_quality_gate.actual_rate is None


def test_final_quality_batch_remains_compatible_with_quality_audit(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    reports_dir = tmp_path / "reports"
    run_dir = tmp_path / "acceptance_run"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)

    run = FinalQualityAcceptanceService(Settings(demo_mode=False)).run_batch(
        FinalQualityBatchConfig(
            num_requests=2,
            output_dir=str(run_dir),
            top_k_size=4,
            base_seed=41,
            candidate_pool_limit=4,
            save_traces=False,
            demo_mode=False,
        )
    )

    report = run_quality_audit(
        run_dir=run_dir,
        normalized_dir=normalized_dir,
        reports_dir=reports_dir,
    )

    assert report.generated_top_k_count == run.summary.top_k.returned_count
    assert report.generated_top_k_count > 0
    assert (reports_dir / "quality_audit_report.json").exists()


def test_build_and_score_solve_playtest_packet(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    playtest_dir = tmp_path / "playtest"
    generated_run_dir = tmp_path / "generated"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    _write_generated_run(generated_run_dir)

    packet = build_solve_playtest_packet(
        run_dir=generated_run_dir,
        normalized_dir=normalized_dir,
        output_dir=playtest_dir,
        tester_count=2,
        boards_per_tester=2,
        seed=19,
    )

    assert (playtest_dir / "solve_playtest_packet.json").exists()
    assert (playtest_dir / "solve_playtest_instructions.md").exists()
    assert (playtest_dir / "solve_playtest_template.csv").exists()
    assert len(packet["tester_packets"]) == 2
    assert all(len(item["boards"]) == 2 for item in packet["tester_packets"])

    responses_path = playtest_dir / "playtest_responses.csv"
    with responses_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tester_id",
                "packet_board_id",
                "solved",
                "mistake_count",
                "fairness_rating",
                "naturalness_rating",
                "publishable",
                "notes",
            ],
        )
        writer.writeheader()
        for tester_packet in packet["tester_packets"]:
            for board in tester_packet["boards"]:
                writer.writerow(
                    {
                        "tester_id": tester_packet["tester_id"],
                        "packet_board_id": board["packet_board_id"],
                        "solved": "yes",
                        "mistake_count": "1",
                        "fairness_rating": "4",
                        "naturalness_rating": "4",
                        "publishable": "yes",
                        "notes": "felt fair",
                    }
                )

    results = score_solve_playtest(
        packet_key_path=playtest_dir / "solve_playtest_key.json",
        response_paths=[responses_path],
        output_dir=playtest_dir,
    )

    assert results["summary"]["response_count"] == 4
    assert results["summary"]["generated_publishable_rate"] >= 0.0
    assert (playtest_dir / "solve_playtest_results.json").exists()
    assert (playtest_dir / "solve_playtest_results.md").exists()
