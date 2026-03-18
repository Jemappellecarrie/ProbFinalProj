"""Solver ensemble scaffold tests."""

from __future__ import annotations

from app.core.enums import GenerationMode, GroupType
from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.solver.ensemble import EnsembleSolverCoordinator
from app.solver.registry import build_demo_solver_registry


def _demo_puzzle() -> PuzzleCandidate:
    groups = [
        GroupCandidate(
            candidate_id="group_semantic",
            group_type=GroupType.SEMANTIC,
            label="Planets",
            rationale="Demo",
            words=["MERCURY", "VENUS", "EARTH", "MARS"],
            word_ids=["w1", "w2", "w3", "w4"],
            source_strategy="mock_semantic_group_generator",
            extraction_mode="mock_demo",
        ),
        GroupCandidate(
            candidate_id="group_lexical",
            group_type=GroupType.LEXICAL,
            label="Starts with SN",
            rationale="Demo",
            words=["SNAP", "SNIP", "SNOW", "SNUG"],
            word_ids=["w5", "w6", "w7", "w8"],
            source_strategy="mock_lexical_group_generator",
            extraction_mode="mock_demo",
        ),
        GroupCandidate(
            candidate_id="group_phonetic",
            group_type=GroupType.PHONETIC,
            label="Rhymes with -AKE",
            rationale="Demo",
            words=["BAKE", "CAKE", "LAKE", "RAKE"],
            word_ids=["w9", "w10", "w11", "w12"],
            source_strategy="mock_phonetic_group_generator",
            extraction_mode="mock_demo",
        ),
        GroupCandidate(
            candidate_id="group_theme",
            group_type=GroupType.THEME,
            label="Pac-Man ghosts",
            rationale="Demo",
            words=["BLINKY", "INKY", "PINKY", "CLYDE"],
            word_ids=["w13", "w14", "w15", "w16"],
            source_strategy="mock_theme_group_generator",
            extraction_mode="mock_demo",
        ),
    ]
    return PuzzleCandidate(
        puzzle_id="puzzle_1",
        board_words=[
            "MERCURY",
            "SNAP",
            "BAKE",
            "BLINKY",
            "VENUS",
            "SNIP",
            "CAKE",
            "INKY",
            "EARTH",
            "SNOW",
            "LAKE",
            "PINKY",
            "MARS",
            "SNUG",
            "RAKE",
            "CLYDE",
        ],
        groups=groups,
    )


def test_demo_solver_ensemble_produces_votes_and_summary() -> None:
    registry = build_demo_solver_registry()
    coordinator = EnsembleSolverCoordinator(registry)
    context = GenerationContext(
        request_id="req_1",
        mode=GenerationMode.DEMO,
        demo_mode=True,
        include_trace=True,
        developer_mode=True,
        seed=17,
    )
    result = coordinator.solve(_demo_puzzle(), context)
    assert len(result.votes) >= 2
    assert result.agreement_summary.total_solvers >= 2
    assert result.primary_solver_name == result.votes[0].solver_name
