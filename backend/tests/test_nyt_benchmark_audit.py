"""Tests for the public NYT benchmark normalization and audit workflow."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.config.settings import Settings
from app.schemas.evaluation_models import BatchEvaluationConfig
from app.scoring.benchmark_audit import (
    load_normalized_benchmark,
    normalize_public_benchmark,
    run_quality_audit,
)
from app.services.evaluation_service import EvaluationService


def _write_hf_csv(path: Path) -> None:
    rows = [
        (101, "2024-01-01", "ALPHA", "GREEK LETTERS", 0, 1, 1),
        (101, "2024-01-01", "BETA", "GREEK LETTERS", 0, 1, 2),
        (101, "2024-01-01", "GAMMA", "GREEK LETTERS", 0, 1, 3),
        (101, "2024-01-01", "DELTA", "GREEK LETTERS", 0, 1, 4),
        (101, "2024-01-01", "MARS", "PLANETS", 1, 2, 1),
        (101, "2024-01-01", "VENUS", "PLANETS", 1, 2, 2),
        (101, "2024-01-01", "EARTH", "PLANETS", 1, 2, 3),
        (101, "2024-01-01", "SATURN", "PLANETS", 1, 2, 4),
        (101, "2024-01-01", "SNAP", "STARTS WITH SN", 2, 3, 1),
        (101, "2024-01-01", "SNIP", "STARTS WITH SN", 2, 3, 2),
        (101, "2024-01-01", "SNOW", "STARTS WITH SN", 2, 3, 3),
        (101, "2024-01-01", "SNUG", "STARTS WITH SN", 2, 3, 4),
        (101, "2024-01-01", "SEE", "LETTER HOMOPHONES", 3, 4, 1),
        (101, "2024-01-01", "WHY", "LETTER HOMOPHONES", 3, 4, 2),
        (101, "2024-01-01", "QUEUE", "LETTER HOMOPHONES", 3, 4, 3),
        (101, "2024-01-01", "ARE", "LETTER HOMOPHONES", 3, 4, 4),
        (102, "2024-01-02", "RED", "COLORS", 0, 1, 1),
        (102, "2024-01-02", "BLUE", "COLORS", 0, 1, 2),
        (102, "2024-01-02", "GREEN", "COLORS", 0, 1, 3),
        (102, "2024-01-02", "YELLOW", "COLORS", 0, 1, 4),
        (102, "2024-01-02", "DOG", "PETS", 1, 2, 1),
        (102, "2024-01-02", "CAT", "PETS", 1, 2, 2),
        (102, "2024-01-02", "FISH", "PETS", 1, 2, 3),
        (102, "2024-01-02", "BIRD", "PETS", 1, 2, 4),
        (102, "2024-01-02", "BOOK", "THINGS WITH PAGES", 2, 3, 1),
        (102, "2024-01-02", "MAGAZINE", "THINGS WITH PAGES", 2, 3, 2),
        (102, "2024-01-02", "CATALOG", "THINGS WITH PAGES", 2, 3, 3),
        (102, "2024-01-02", "MANUAL", "THINGS WITH PAGES", 2, 3, 4),
        (102, "2024-01-02", "HEEL", "RHYMES WITH EEL", 3, 4, 1),
        (102, "2024-01-02", "KEEL", "RHYMES WITH EEL", 3, 4, 2),
        (102, "2024-01-02", "PEEL", "RHYMES WITH EEL", 3, 4, 3),
        (102, "2024-01-02", "REEL", "RHYMES WITH EEL", 3, 4, 4),
        (103, "2024-01-03", "MERCURY", "PLANETS", 0, 1, 1),
        (103, "2024-01-03", "JUPITER", "PLANETS", 0, 1, 2),
        (103, "2024-01-03", "NEPTUNE", "PLANETS", 0, 1, 3),
        (103, "2024-01-03", "URANUS", "PLANETS", 0, 1, 4),
        (103, "2024-01-03", "COPPER", "METALS", 1, 2, 1),
        (103, "2024-01-03", "IRON", "METALS", 1, 2, 2),
        (103, "2024-01-03", "SILVER", "METALS", 1, 2, 3),
        (103, "2024-01-03", "GOLD", "METALS", 1, 2, 4),
        (103, "2024-01-03", "APPLE", "FRUITS", 2, 3, 1),
        (103, "2024-01-03", "PEAR", "FRUITS", 2, 3, 2),
        (103, "2024-01-03", "PLUM", "FRUITS", 2, 3, 3),
        (103, "2024-01-03", "GRAPE", "FRUITS", 2, 3, 4),
        (103, "2024-01-03", "SPIN", "STARTS WITH SP", 3, 4, 1),
        (103, "2024-01-03", "SPAN", "STARTS WITH SP", 3, 4, 2),
        (103, "2024-01-03", "SPOT", "STARTS WITH SP", 3, 4, 3),
        (103, "2024-01-03", "SPUR", "STARTS WITH SP", 3, 4, 4),
        (104, "2024-01-04", "CO", "STATE ABBREVIATIONS", 0, 1, 1),
        (104, "2024-01-04", "MA", "STATE ABBREVIATIONS", 0, 1, 2),
        (104, "2024-01-04", "ME", "STATE ABBREVIATIONS", 0, 1, 3),
        (104, "2024-01-04", "PA", "STATE ABBREVIATIONS", 0, 1, 4),
        (104, "2024-01-04", "DO", "MUSICAL NOTES", 1, 2, 1),
        (104, "2024-01-04", "FA", "MUSICAL NOTES", 1, 2, 2),
        (104, "2024-01-04", "LA", "MUSICAL NOTES", 1, 2, 3),
        (104, "2024-01-04", "TI", "MUSICAL NOTES", 1, 2, 4),
        (104, "2024-01-04", "MU", "GREEK LETTERS", 2, 3, 1),
        (104, "2024-01-04", "NU", "GREEK LETTERS", 2, 3, 2),
        (104, "2024-01-04", "PI", "GREEK LETTERS", 2, 3, 3),
        (104, "2024-01-04", "XI", "GREEK LETTERS", 2, 3, 4),
        (104, "2024-01-04", "FE", "PERIODIC TABLE SYMBOLS", 3, 4, 1),
        (104, "2024-01-04", "HE", "PERIODIC TABLE SYMBOLS", 3, 4, 2),
        (104, "2024-01-04", "", "PERIODIC TABLE SYMBOLS", 3, 4, 3),
        (104, "2024-01-04", "NI", "PERIODIC TABLE SYMBOLS", 3, 4, 4),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Game ID",
                "Puzzle Date",
                "Word",
                "Group Name",
                "Group Level",
                "Starting Row",
                "Starting Column",
            ]
        )
        writer.writerows(rows)


def _write_github_json(path: Path) -> None:
    payload = [
        {
            "id": 104,
            "date": "2024-01-04",
            "answers": [
                {
                    "level": 0,
                    "group": "STATE ABBREVIATIONS",
                    "members": ["CO", "MA", "ME", "PA"],
                },
                {
                    "level": 1,
                    "group": "MUSICAL NOTES",
                    "members": ["DO", "FA", "LA", "TI"],
                },
                {
                    "level": 2,
                    "group": "GREEK LETTERS",
                    "members": ["MU", "NU", "PI", "XI"],
                },
                {
                    "level": 3,
                    "group": "PERIODIC TABLE SYMBOLS",
                    "members": ["FE", "HE", "NA", "NI"],
                },
            ],
        },
        {
            "id": 105,
            "date": "2024-01-05",
            "answers": [
                {
                    "level": 0,
                    "group": "STONE FRUITS",
                    "members": ["APRICOT", "CHERRY", "PEACH", "PLUM"],
                },
                {
                    "level": 1,
                    "group": "BOARD GAMES",
                    "members": ["CHESS", "GO", "RISK", "SORRY"],
                },
                {
                    "level": 2,
                    "group": "STARTS WITH TR",
                    "members": ["TRACE", "TRACK", "TRAIL", "TRIP"],
                },
                {
                    "level": 3,
                    "group": "RHYMES WITH OAT",
                    "members": ["BOAT", "COAT", "FLOAT", "GOAT"],
                },
            ],
        },
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_source_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "source": "huggingface",
                "dataset_id": "eric27n/NYT-Connections",
                "rows": 64,
                "games": 4,
                "columns": [
                    "Game ID",
                    "Puzzle Date",
                    "Word",
                    "Group Name",
                    "Group Level",
                    "Starting Row",
                    "Starting Column",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_benchmark_fixture(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    _write_hf_csv(raw_dir / "nyt_connections_hf.csv")
    _write_github_json(raw_dir / "nyt_connections_answers_github.json")
    _write_source_manifest(raw_dir / "source_manifest.json")
    (raw_dir / "nyt_connections_hf.parquet").write_text("broken parquet", encoding="utf-8")


def test_normalize_public_benchmark_repairs_and_splits_deterministically(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    _write_benchmark_fixture(raw_dir)

    first = normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    second = normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)

    assert first.manifest.board_count == 5
    assert first.manifest.primary_board_count == 4
    assert first.manifest.supplement_board_count == 1
    assert first.manifest.repaired_board_count == 1
    assert first.manifest.primary_source_dataset == "eric27n/NYT-Connections"
    assert first.manifest.load_notes
    assert "csv_fallback_used" in first.manifest.load_notes

    repaired_board = next(board for board in first.boards if board.source_game_id == "104")
    repaired_group = next(group for group in repaired_board.groups if group.level == 3)
    assert repaired_group.words == ["FE", "HE", "NA", "NI"]
    assert repaired_group.color == "purple"
    assert len(repaired_board.board_words) == 16
    assert len(set(repaired_board.board_words)) == 16
    assert repaired_board.board_signature == second.boards[3].board_signature
    assert repaired_board.solution_signature == second.boards[3].solution_signature

    assert first.calibration_split.board_ids == [
        "nyt_connections_2024-01-01_101",
        "nyt_connections_2024-01-02_102",
        "nyt_connections_2024-01-03_103",
    ]
    assert first.holdout_split.board_ids == ["nyt_connections_2024-01-04_104"]
    assert first.freshness_split is not None
    assert first.freshness_split.board_ids == ["nyt_connections_2024-01-05_105"]

    assert (normalized_dir / "boards_v1.jsonl").exists()
    assert (normalized_dir / "boards_v1.parquet").exists()
    assert (normalized_dir / "benchmark_manifest.json").exists()
    assert (normalized_dir / "calibration_split.json").exists()
    assert (normalized_dir / "holdout_split.json").exists()
    assert (normalized_dir / "freshness_split.json").exists()


def test_load_normalized_benchmark_reads_stable_board_order(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    _write_benchmark_fixture(raw_dir)

    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    boards = load_normalized_benchmark(normalized_dir)

    assert [board.benchmark_board_id for board in boards] == [
        "nyt_connections_2024-01-01_101",
        "nyt_connections_2024-01-02_102",
        "nyt_connections_2024-01-03_103",
        "nyt_connections_2024-01-04_104",
        "nyt_connections_2024-01-05_105",
    ]
    assert boards[-1].source_dataset == "github_json_supplement"


def test_run_quality_audit_consumes_generated_eval_artifacts(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    reports_dir = tmp_path / "reports"
    eval_dir = tmp_path / "eval_run"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)

    service = EvaluationService(Settings(demo_mode=False))
    service.evaluate_batch(
        BatchEvaluationConfig(
            num_puzzles=2,
            output_dir=str(eval_dir),
            save_traces=False,
            top_k_size=1,
            base_seed=11,
            demo_mode=False,
        )
    )

    report = run_quality_audit(
        run_dir=eval_dir,
        normalized_dir=normalized_dir,
        reports_dir=reports_dir,
    )

    assert report.generated_run_id
    assert report.generated_top_k_count == 1
    assert report.generated_quality_buckets["accepted_high_confidence"] >= 0
    assert report.benchmark_holdout_count == 1
    assert "verification_decision_distribution" in report.comparison_sections
    assert "style_distance_summary" in report.comparison_sections
    assert "machine_publishable_proxy" in report.quality_gate_summary
    assert "style_metric_inflation_flags" in report.comparison_sections
    assert "benchmark_anchor_warnings" in report.comparison_sections

    report_json = json.loads((reports_dir / "quality_audit_report.json").read_text())
    comparison_json = json.loads((reports_dir / "generated_vs_nyt_comparison.json").read_text())
    benchmark_json = json.loads((reports_dir / "nyt_benchmark_summary.json").read_text())

    assert report_json["generated_run_id"] == report.generated_run_id
    assert comparison_json["generated_run_id"] == report.generated_run_id
    assert benchmark_json["holdout_split"]["count"] == 1
    assert isinstance(report_json["comparison_sections"]["style_metric_inflation_flags"], list)
    assert isinstance(report_json["comparison_sections"]["benchmark_anchor_warnings"], list)
    assert (reports_dir / "quality_audit_report.md").exists()
