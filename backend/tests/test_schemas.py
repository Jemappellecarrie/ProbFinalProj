"""Schema validation tests for core models."""

from __future__ import annotations

from app.core.enums import GroupType
from app.schemas.evaluation_models import AmbiguityEvidence, AmbiguityReport, AmbiguityRiskLevel
from app.schemas.feature_models import WordEntry
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate, PuzzleScore, VerificationResult


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
    puzzle = PuzzleCandidate(
        puzzle_id="puzzle_1",
        board_words=[
            "MERCURY",
            "VENUS",
            "EARTH",
            "MARS",
            "SNAP",
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
    assert len(puzzle.groups) == 4


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
    verification = VerificationResult(passed=True, ambiguity_report=report)
    assert verification.ambiguity_report is not None


def test_puzzle_score_accepts_style_analysis_placeholder() -> None:
    score = PuzzleScore(
        scorer_name="mock_puzzle_scorer",
        overall=0.9,
        coherence=0.9,
        ambiguity_penalty=0.0,
    )
    assert score.overall == 0.9
