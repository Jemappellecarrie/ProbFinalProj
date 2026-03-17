"""Schema validation tests for core models."""

from __future__ import annotations

from app.core.enums import GroupType
from app.schemas.feature_models import WordEntry
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate


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
