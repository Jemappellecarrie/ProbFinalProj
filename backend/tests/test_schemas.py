"""Schema validation tests for core models."""

from __future__ import annotations

import pytest

from app.core.enums import GroupType
from app.schemas.evaluation_models import (
    AmbiguityEvidence,
    AmbiguityReport,
    AmbiguityRiskLevel,
    RankedPuzzleRecord,
    ScoreBreakdownView,
)
from app.schemas.feature_models import WordEntry
from app.schemas.puzzle_models import (
    GroupCandidate,
    PuzzleCandidate,
    PuzzleScore,
    VerificationResult,
)


def test_group_candidate_requires_four_words() -> None:
    candidate = GroupCandidate(
        candidate_id="group_1",
        group_type=GroupType.SEMANTIC,
        label="Planets",
        rationale="Demo",
        words=["MERCURY", "VENUS", "EARTH", "MARS"],
        word_ids=["w1", "w2", "w3", "w4"],
        source_strategy="demo",
        extraction_mode="mock_demo",
    )
    assert candidate.label == "Planets"


def test_puzzle_candidate_contains_four_groups() -> None:
    planets = GroupCandidate(
        candidate_id="group_1",
        group_type=GroupType.SEMANTIC,
        label="Planets",
        rationale="Demo",
        words=["MERCURY", "VENUS", "EARTH", "MARS"],
        word_ids=["w1", "w2", "w3", "w4"],
        source_strategy="demo",
        extraction_mode="mock_demo",
    )
    gems = GroupCandidate(
        candidate_id="group_2",
        group_type=GroupType.SEMANTIC,
        label="Gemstones",
        rationale="Demo",
        words=["RUBY", "OPAL", "JADE", "TOPAZ"],
        word_ids=["w5", "w6", "w7", "w8"],
        source_strategy="demo",
        extraction_mode="mock_demo",
    )
    ghosts = GroupCandidate(
        candidate_id="group_3",
        group_type=GroupType.THEME,
        label="Ghosts",
        rationale="Demo",
        words=["BLINKY", "INKY", "PINKY", "CLYDE"],
        word_ids=["w9", "w10", "w11", "w12"],
        source_strategy="demo",
        extraction_mode="mock_demo",
    )
    turtles = GroupCandidate(
        candidate_id="group_4",
        group_type=GroupType.THEME,
        label="Turtles",
        rationale="Demo",
        words=["LEONARDO", "DONATELLO", "RAPHAEL", "MICHELANGELO"],
        word_ids=["w13", "w14", "w15", "w16"],
        source_strategy="demo",
        extraction_mode="mock_demo",
    )
    puzzle = PuzzleCandidate(
        puzzle_id="puzzle_1",
        board_words=[
            "MERCURY",
            "VENUS",
            "EARTH",
            "MARS",
            "RUBY",
            "OPAL",
            "JADE",
            "TOPAZ",
            "BLINKY",
            "INKY",
            "PINKY",
            "CLYDE",
            "LEONARDO",
            "DONATELLO",
            "RAPHAEL",
            "MICHELANGELO",
        ],
        groups=[planets, gems, ghosts, turtles],
    )
    assert len(puzzle.groups) == 4


def test_group_candidate_rejects_duplicate_words_and_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="unique"):
        GroupCandidate(
            candidate_id="group_dup",
            group_type=GroupType.SEMANTIC,
            label="Duplicate Words",
            rationale="Demo",
            words=["MERCURY", "MERCURY", "EARTH", "MARS"],
            word_ids=["w1", "w2", "w3", "w4"],
            source_strategy="demo",
            extraction_mode="mock_demo",
        )

    with pytest.raises(ValueError, match=r"between 0\.0 and 1\.0"):
        GroupCandidate(
            candidate_id="group_conf",
            group_type=GroupType.SEMANTIC,
            label="Bad Confidence",
            rationale="Demo",
            words=["MERCURY", "VENUS", "EARTH", "MARS"],
            word_ids=["w1", "w2", "w3", "w4"],
            source_strategy="demo",
            extraction_mode="mock_demo",
            confidence=1.2,
        )


def test_puzzle_candidate_rejects_duplicate_board_words() -> None:
    group = GroupCandidate(
        candidate_id="group_1",
        group_type=GroupType.SEMANTIC,
        label="Planets",
        rationale="Demo",
        words=["MERCURY", "VENUS", "EARTH", "MARS"],
        word_ids=["w1", "w2", "w3", "w4"],
        source_strategy="demo",
        extraction_mode="mock_demo",
    )

    with pytest.raises(ValueError, match="unique"):
        PuzzleCandidate(
            puzzle_id="puzzle_dup",
            board_words=[
                "MERCURY",
                "VENUS",
                "EARTH",
                "MARS",
                "MERCURY",
                "SNIP",
                "SNOW",
                "SNUG",
                "BAKE",
                "CAKE",
                "LAKE",
                "RAKE",
                "BLINKY",
                "INKY",
                "PINKY",
                "CLYDE",
            ],
            groups=[group, group, group, group],
        )


def test_word_entry_accepts_group_hints() -> None:
    entry = WordEntry(
        word_id="word_1",
        surface_form="MERCURY",
        normalized="mercury",
        known_group_hints={"semantic": "planets"},
    )
    assert entry.known_group_hints["semantic"] == "planets"


def test_verification_result_accepts_ambiguity_report() -> None:
    report = AmbiguityReport(
        evaluator_name="baseline_ambiguity_evaluator",
        risk_level=AmbiguityRiskLevel.LOW,
        penalty_hint=0.0,
        reject_recommended=False,
        summary="Demo",
        evidence=AmbiguityEvidence(),
    )
    verification = VerificationResult(
        passed=True,
        decision="borderline",
        warning_flags=["moderate_leakage"],
        summary_metrics={"board_pressure": 0.28},
        evidence_refs=["board_summary"],
        ambiguity_report=report,
    )
    assert verification.ambiguity_report is not None
    assert verification.decision == "borderline"
    assert verification.warning_flags == ["moderate_leakage"]
    assert verification.summary_metrics["board_pressure"] == 0.28
    assert verification.evidence_refs == ["board_summary"]


def test_puzzle_score_accepts_style_analysis_placeholder() -> None:
    score = PuzzleScore(
        scorer_name="mock_puzzle_scorer",
        overall=0.9,
        coherence=0.9,
        ambiguity_penalty=0.0,
    )
    assert score.overall == 0.9


def test_ranked_puzzle_record_accepts_mechanism_mix_metadata() -> None:
    record = RankedPuzzleRecord(
        rank=1,
        puzzle_id="puzzle_stage2",
        accepted=True,
        board_words=[f"W{i}" for i in range(16)],
        group_labels=["Planets", "Starts with SN", "Ends with -ASH", "Pac-Man ghosts"],
        group_types=["semantic", "lexical", "lexical", "theme"],
        mechanism_mix_summary={"lexical": 2, "semantic": 1, "theme": 1},
        mixed_board=True,
        score_breakdown=ScoreBreakdownView(
            overall=0.8,
            coherence=0.82,
            ambiguity_penalty=0.12,
            components={"composer_ranking_score": 3.4},
        ),
    )
    assert record.mixed_board is True
    assert record.mechanism_mix_summary["lexical"] == 2
