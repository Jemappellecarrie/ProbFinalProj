"""Tests for blind review packet generation and scoring."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.scoring.benchmark_audit import normalize_public_benchmark
from app.scoring.blind_review import build_blind_review_packet, score_blind_review

from .test_nyt_benchmark_audit import _write_benchmark_fixture


def _write_generated_run(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    accepted = [
        {
            "iteration_index": 0,
            "request_seed": 17,
            "puzzle_id": "generated_alpha",
            "board_words": [
                "RUBY",
                "OPAL",
                "JADE",
                "TOPAZ",
                "SNAP",
                "SNIP",
                "SNOW",
                "SNUG",
                "HEEL",
                "KEEL",
                "PEEL",
                "REEL",
                "LEONARDO",
                "DONATELLO",
                "RAPHAEL",
                "MICHELANGELO",
            ],
            "group_labels": [
                "Gemstones",
                "Starts with SN",
                "Rhymes with EEL",
                "Teenage Mutant Ninja Turtles",
            ],
            "group_word_sets": [
                ["RUBY", "OPAL", "JADE", "TOPAZ"],
                ["SNAP", "SNIP", "SNOW", "SNUG"],
                ["HEEL", "KEEL", "PEEL", "REEL"],
                ["LEONARDO", "DONATELLO", "RAPHAEL", "MICHELANGELO"],
            ],
            "group_types": ["semantic", "lexical", "phonetic", "theme"],
            "mechanism_mix_summary": {
                "semantic": 1,
                "lexical": 1,
                "phonetic": 1,
                "theme": 1,
            },
            "mixed_board": True,
            "verification_decision": "accept",
            "score_breakdown": {
                "overall": 0.88,
                "coherence": 0.84,
                "ambiguity_penalty": 0.12,
                "human_likeness": 0.79,
                "components": {"composer_ranking_score": 0.81},
            },
            "ambiguity_report": {
                "risk_level": "low",
                "penalty_hint": 0.12,
                "summary": "Low ambiguity.",
                "evaluator_name": "fixture",
                "reject_recommended": False,
                "evidence": {"triggered_flags": []},
                "notes": [],
                "metadata": {},
            },
            "style_analysis": {
                "board_style_summary": {
                    "board_archetype": "balanced_mixed",
                    "style_alignment_score": 0.77,
                    "monotony_score": 0.0,
                    "metrics": {
                        "unique_group_type_count": 4.0,
                        "wordplay_group_count": 2.0,
                    },
                    "mechanism_mix_profile": {
                        "counts": {
                            "semantic": 1,
                            "lexical": 1,
                            "phonetic": 1,
                            "theme": 1,
                        },
                        "shares": {
                            "semantic": 0.25,
                            "lexical": 0.25,
                            "phonetic": 0.25,
                            "theme": 0.25,
                        },
                        "unique_group_type_count": 4,
                        "semantic_group_count": 1,
                        "lexical_group_count": 1,
                        "phonetic_group_count": 1,
                        "theme_group_count": 1,
                        "wordplay_group_count": 2,
                        "mixed_board": True,
                    },
                    "group_archetypes": [],
                    "label_token_mean": 2.0,
                    "label_token_std": 0.5,
                    "label_consistency": 0.75,
                    "evidence_interpretability": 0.9,
                    "semantic_wordplay_balance": 0.67,
                    "archetype_diversity": 1.0,
                    "redundancy_score": 0.1,
                    "coherence_trickiness_balance": 0.8,
                    "out_of_band_flags": [],
                    "notes": [],
                },
                "out_of_band_flags": [],
                "group_style_summaries": [],
                "signals": [],
                "analyzer_name": "fixture",
                "archetype": {"label": "balanced_mixed", "rationale": "fixture", "flags": []},
                "nyt_likeness": {"score": 0.77, "notes": []},
                "mechanism_mix_profile": {
                    "counts": {"semantic": 1, "lexical": 1, "phonetic": 1, "theme": 1},
                    "shares": {
                        "semantic": 0.25,
                        "lexical": 0.25,
                        "phonetic": 0.25,
                        "theme": 0.25,
                    },
                    "unique_group_type_count": 4,
                    "semantic_group_count": 1,
                    "lexical_group_count": 1,
                    "phonetic_group_count": 1,
                    "theme_group_count": 1,
                    "wordplay_group_count": 2,
                    "mixed_board": True,
                },
                "style_target_comparison": [],
                "notes": [],
                "metadata": {},
            },
            "warnings": [],
            "selected_components": {},
            "notes": [],
        }
    ]
    top_k = {
        "requested_k": 1,
        "returned_count": 1,
        "ranked_puzzles": [
            {
                "rank": 1,
                "puzzle_id": "generated_alpha",
                "accepted": True,
                "verification_decision": "accept",
                "board_words": accepted[0]["board_words"],
                "group_labels": accepted[0]["group_labels"],
                "group_word_sets": accepted[0]["group_word_sets"],
                "group_types": accepted[0]["group_types"],
                "mechanism_mix_summary": accepted[0]["mechanism_mix_summary"],
                "mixed_board": True,
                "score_breakdown": accepted[0]["score_breakdown"],
                "ambiguity_risk_level": "low",
                "ambiguity_penalty_hint": 0.12,
                "solver_agreement_ratio": 1.0,
                "solver_disagreement_flags": [],
                "style_archetype": "balanced_mixed",
                "nyt_likeness_placeholder": 0.77,
                "style_alignment_score": 0.77,
                "style_out_of_band_flags": [],
                "ranking_influence_notes": [],
                "trace_id": None,
                "reject_risk_flags": [],
                "notes": [],
            }
        ],
        "notes": [],
    }
    summary = {
        "run_id": "eval_fixture",
        "created_at": "2026-03-25T00:00:00Z",
        "total_generated": 1,
        "accepted_count": 1,
        "rejected_count": 0,
        "acceptance_rate": 1.0,
        "reject_reason_histogram": {"counts": {}},
        "generator_mix": {
            "group_type_counts": {"semantic": 1, "lexical": 1, "phonetic": 1, "theme": 1},
            "generator_strategy_counts": {},
            "board_mix_counts": {"mixed": 1},
            "board_type_signature_counts": {"lexical+phonetic+semantic+theme": 1},
        },
        "score_distribution": {
            "average_overall": 0.88,
            "average_coherence": 0.84,
            "average_ambiguity_penalty": 0.12,
            "average_human_likeness": 0.79,
            "min_overall": 0.88,
            "max_overall": 0.88,
        },
        "ambiguity_risk_distribution": {"low": 1},
        "solver_agreement_statistics": {
            "total_ensemble_runs": 0,
            "unanimous_target_match_count": 0,
            "disagreement_count": 0,
            "average_agreement_ratio": 0.0,
        },
        "top_k": top_k,
        "calibration_summary": None,
        "output_dir": str(run_dir),
        "notes": [],
    }

    (run_dir / "accepted.json").write_text(json.dumps(accepted, indent=2), encoding="utf-8")
    (run_dir / "rejected.json").write_text("[]", encoding="utf-8")
    (run_dir / "top_k.json").write_text(json.dumps(top_k, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "packet_board_id",
                "reviewer_id",
                "unique_clear_grouping",
                "fair_not_forced",
                "labels_feel_natural",
                "aha_satisfaction",
                "publishable",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_build_blind_review_packet_hides_source_and_is_deterministic(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    review_dir = tmp_path / "review_packets"
    generated_run_dir = tmp_path / "generated"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    _write_generated_run(generated_run_dir)

    first = build_blind_review_packet(
        run_dir=generated_run_dir,
        normalized_dir=normalized_dir,
        output_dir=review_dir,
        generated_count=1,
        benchmark_count=1,
        seed=23,
    )
    second = build_blind_review_packet(
        run_dir=generated_run_dir,
        normalized_dir=normalized_dir,
        output_dir=review_dir,
        generated_count=1,
        benchmark_count=1,
        seed=23,
    )

    assert [entry.packet_board_id for entry in first.packet.entries] == [
        "blind_board_001",
        "blind_board_002",
    ]
    assert [entry.packet_board_id for entry in first.packet.entries] == [
        entry.packet_board_id for entry in second.packet.entries
    ]
    assert "generated" not in (review_dir / "blind_review_packet.json").read_text().lower()
    assert "benchmark" not in (review_dir / "blind_review_packet.json").read_text().lower()
    assert (review_dir / "blind_review_key.json").exists()
    assert (review_dir / "blind_review_instructions.md").exists()


def test_build_blind_review_packet_reports_shortfall_and_writes_template(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    review_dir = tmp_path / "review_packets"
    generated_run_dir = tmp_path / "generated"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    _write_generated_run(generated_run_dir)

    bundle = build_blind_review_packet(
        run_dir=generated_run_dir,
        normalized_dir=normalized_dir,
        output_dir=review_dir,
        generated_count=3,
        benchmark_count=2,
        seed=23,
    )

    packet_payload = json.loads((review_dir / "blind_review_packet.json").read_text())

    assert len(bundle.packet.entries) == 2
    assert any("shortfall" in note.lower() for note in packet_payload["notes"])
    assert (review_dir / "reviewer_template.csv").exists()


def test_score_blind_review_computes_publishable_rates_and_gate(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    normalized_dir = tmp_path / "normalized"
    review_dir = tmp_path / "review_packets"
    results_dir = tmp_path / "results"
    generated_run_dir = tmp_path / "generated"
    _write_benchmark_fixture(raw_dir)
    normalize_public_benchmark(raw_dir=raw_dir, normalized_dir=normalized_dir)
    _write_generated_run(generated_run_dir)

    packet_bundle = build_blind_review_packet(
        run_dir=generated_run_dir,
        normalized_dir=normalized_dir,
        output_dir=review_dir,
        generated_count=1,
        benchmark_count=1,
        seed=23,
    )
    answer_key = {
        entry.packet_board_id: entry.hidden_source.source_label
        for entry in packet_bundle.answer_key.entries
    }
    generated_id = next(key for key, value in answer_key.items() if value == "generated")
    benchmark_id = next(key for key, value in answer_key.items() if value == "benchmark")

    reviewer_one = review_dir / "reviewer_one.csv"
    reviewer_two = review_dir / "reviewer_two.csv"
    _write_review_csv(
        reviewer_one,
        [
            {
                "packet_board_id": generated_id,
                "reviewer_id": "r1",
                "unique_clear_grouping": "yes",
                "fair_not_forced": "4",
                "labels_feel_natural": "4",
                "aha_satisfaction": "4",
                "publishable": "yes",
                "notes": "clean and fair",
            },
            {
                "packet_board_id": benchmark_id,
                "reviewer_id": "r1",
                "unique_clear_grouping": "yes",
                "fair_not_forced": "5",
                "labels_feel_natural": "5",
                "aha_satisfaction": "5",
                "publishable": "yes",
                "notes": "excellent baseline",
            },
        ],
    )
    _write_review_csv(
        reviewer_two,
        [
            {
                "packet_board_id": generated_id,
                "reviewer_id": "r2",
                "unique_clear_grouping": "no",
                "fair_not_forced": "2",
                "labels_feel_natural": "2",
                "aha_satisfaction": "2",
                "publishable": "no",
                "notes": "felt forced and ambiguous",
            },
            {
                "packet_board_id": benchmark_id,
                "reviewer_id": "r2",
                "unique_clear_grouping": "yes",
                "fair_not_forced": "5",
                "labels_feel_natural": "5",
                "aha_satisfaction": "4",
                "publishable": "yes",
                "notes": "clear and satisfying",
            },
        ],
    )

    results = score_blind_review(
        answer_key_path=review_dir / "blind_review_key.json",
        review_paths=[reviewer_one, reviewer_two],
        output_dir=results_dir,
    )

    assert results.generated_publishable_rate == 0.0
    assert results.benchmark_publishable_rate == 1.0
    assert results.final_quality_gate.gate_name == "generated_publishable_majority_40_percent"
    assert results.final_quality_gate.passed is False
    assert results.final_quality_gate.actual_rate == 0.0
    assert results.inter_rater_agreement["publishable_pairwise_agreement"] == 0.5

    result_json = json.loads((results_dir / "blind_review_results.json").read_text())
    gate_json = json.loads((results_dir / "final_quality_gate.json").read_text())

    assert result_json["generated_publishable_rate"] == 0.0
    assert gate_json["threshold_rate"] == 0.4
    assert gate_json["passed"] is False
    assert (results_dir / "blind_review_results.md").exists()
