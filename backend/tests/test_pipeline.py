"""Pipeline orchestration tests using demo-mode components."""

from __future__ import annotations

from app.config.settings import Settings
from app.core.enums import GroupType, VerificationDecision
from app.domain.value_objects import GenerationContext
from app.pipeline.orchestration import PuzzleGenerationPipeline
from app.schemas.api import PuzzleGenerationRequest
from app.schemas.puzzle_models import (
    GroupCandidate,
    PuzzleCandidate,
    PuzzleScore,
    VerificationResult,
)
from app.services.generation_service import GenerationService


def test_demo_pipeline_generates_complete_puzzle() -> None:
    service = GenerationService(Settings())
    response = service.generate_puzzle(PuzzleGenerationRequest())

    assert response.demo_mode is True
    assert len(response.puzzle.groups) == 4
    assert len(response.puzzle.board_words) == 16
    assert len(set(response.puzzle.board_words)) == 16
    assert response.score.overall >= 0.0
    assert response.verification.ambiguity_report is not None
    assert response.verification.ensemble_result is not None
    assert response.score.style_analysis is not None


def test_semantic_baseline_pipeline_generates_complete_puzzle() -> None:
    service = GenerationService(Settings(demo_mode=False))
    response = service.generate_puzzle(
        PuzzleGenerationRequest(requested_group_types=[GroupType.SEMANTIC], seed=17)
    )

    assert response.demo_mode is False
    assert response.selected_components["feature_extractor"] == "human_curated_feature_extractor"
    assert response.selected_components["composer"] == "human_puzzle_composer"
    assert response.selected_components["verifier"] == "internal_puzzle_verifier"
    assert response.selected_components["scorer"] == "human_owned_puzzle_scorer"
    assert len(response.puzzle.groups) == 4
    assert len(response.puzzle.board_words) == 16
    assert len(set(response.puzzle.board_words)) == 16
    assert all(group.group_type is GroupType.SEMANTIC for group in response.puzzle.groups)
    assert response.verification.ambiguity_report is not None
    assert response.verification.decision in {"accept", "borderline"}
    assert "group_coherence" in response.score.components
    assert response.score.style_analysis is not None


def test_semantic_baseline_pipeline_prefers_semantic_majority_board_by_default() -> None:
    service = GenerationService(Settings(demo_mode=False))

    response = service.generate_puzzle(PuzzleGenerationRequest(seed=17, include_trace=True))

    assert response.demo_mode is False
    assert response.selected_components["generators"] == [
        "human_semantic_group_generator",
        "human_lexical_group_generator",
        "human_phonetic_group_generator",
        "human_theme_group_generator",
    ]
    assert response.puzzle.metadata["semantic_group_count"] >= 2
    assert response.puzzle.metadata["semantic_majority_board"] is True
    assert "semantic_majority_preference" in response.puzzle.metadata["composition_trace"][
        "selection_policy"
    ]
    assert "winner_editorial_family_repeat_count" in response.puzzle.metadata["composition_trace"][
        "selection_policy"
    ]
    assert response.score.style_analysis is not None
    assert response.score.style_analysis.board_style_summary is not None
    assert response.score.style_analysis.style_target_comparison
    assert response.trace is not None
    assert response.trace.metadata["selection_summary"]["semantic_group_count"] >= 2
    assert response.trace.metadata["selection_summary"]["mixed_board"] in {True, False}
    assert response.trace.metadata["selection_summary"]["verification_decision"] in {
        "accept",
        "borderline",
        "reject",
    }


def test_pipeline_selection_key_demotes_repeated_winner_families() -> None:
    dummy_groups = [
        GroupCandidate(
            candidate_id=f"candidate_{index}",
            group_type=GroupType.SEMANTIC,
            label=f"Group {index}",
            rationale="fixture",
            words=[f"W{index}_{word_index}" for word_index in range(4)],
            word_ids=[f"word_{index}_{word_index}" for word_index in range(4)],
            source_strategy="test",
            extraction_mode="test",
            confidence=0.9,
            metadata={"rule_signature": f"semantic:group_{index}"},
        )
        for index in range(4)
    ]
    context = GenerationContext(
        request_id="req_winner_selection",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=GroupType.ordered(),
        run_metadata={
            "editorial_run_state": {
                "winner_family_count_by_run": {
                    "editorial": {"editorial_family_repeat": 1},
                    "template": {"template_repeat": 1},
                    "theme": {"theme:pac_man_ghosts": 1},
                    "surface": {
                        "lexical:shared_suffix:ake": 1,
                        "phonetic:perfect_rhyme:ae1_sh": 1,
                    },
                }
            }
        },
    )
    repeated = PuzzleCandidate(
        puzzle_id="puzzle_repeat",
        board_words=[f"R{index}" for index in range(16)],
        groups=[
            group.model_copy(
                update={
                    "words": [f"R{group_index * 4 + word_index}" for word_index in range(4)],
                    "word_ids": [
                        f"repeat_{group_index}_{word_index}" for word_index in range(4)
                    ],
                }
            )
            for group_index, group in enumerate(dummy_groups)
        ],
        metadata={
            "semantic_majority_board": False,
            "balanced_mixed_board": True,
            "editorial_family_signature": "editorial_family_repeat",
            "mechanism_template_signature": "template_repeat",
            "theme_family_signatures": ["theme:pac_man_ghosts"],
            "surface_wordplay_family_signatures": [
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
            ],
            "ranking_score": 0.96,
        },
    )
    fresh = PuzzleCandidate(
        puzzle_id="puzzle_fresh",
        board_words=[f"F{index}" for index in range(16)],
        groups=[
            group.model_copy(
                update={
                    "words": [f"F{group_index * 4 + word_index}" for word_index in range(4)],
                    "word_ids": [
                        f"fresh_{group_index}_{word_index}" for word_index in range(4)
                    ],
                }
            )
            for group_index, group in enumerate(dummy_groups)
        ],
        metadata={
            "semantic_majority_board": True,
            "balanced_mixed_board": False,
            "editorial_family_signature": "editorial_family_fresh",
            "mechanism_template_signature": "template_fresh",
            "theme_family_signatures": [],
            "surface_wordplay_family_signatures": [],
            "ranking_score": 0.95,
        },
    )
    verification = VerificationResult(
        passed=True,
        decision=VerificationDecision.ACCEPT,
        ambiguity_score=0.08,
        leakage_estimate=0.02,
    )
    repeated_score = PuzzleScore(
        scorer_name="test",
        overall=0.96,
        coherence=0.9,
        ambiguity_penalty=0.08,
        components={},
    )
    fresh_score = PuzzleScore(
        scorer_name="test",
        overall=0.95,
        coherence=0.9,
        ambiguity_penalty=0.08,
        components={},
    )

    repeated_key = PuzzleGenerationPipeline._selection_key(
        repeated,
        verification,
        repeated_score,
        context=context,
        demo_mode=False,
    )
    fresh_key = PuzzleGenerationPipeline._selection_key(
        fresh,
        verification,
        fresh_score,
        context=context,
        demo_mode=False,
    )

    assert fresh_key < repeated_key


def test_pipeline_selection_key_uses_recent_winner_history_to_break_near_ties() -> None:
    dummy_groups = [
        GroupCandidate(
            candidate_id=f"recent_candidate_{index}",
            group_type=GroupType.SEMANTIC,
            label=f"Recent Group {index}",
            rationale="fixture",
            words=[f"RW{index}_{word_index}" for word_index in range(4)],
            word_ids=[f"recent_word_{index}_{word_index}" for word_index in range(4)],
            source_strategy="test",
            extraction_mode="test",
            confidence=0.9,
            metadata={"rule_signature": f"semantic:recent_group_{index}"},
        )
        for index in range(4)
    ]
    context = GenerationContext(
        request_id="req_recent_history",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=23,
        requested_group_types=GroupType.ordered(),
        run_metadata={
            "editorial_run_state": {
                "winner_family_count_by_run": {
                    "board": {},
                    "editorial": {},
                    "theme": {},
                    "surface": {},
                    "template": {},
                },
                "winner_recent_history": {
                    "board": ["board_family_repeat", "board_family_repeat"],
                    "editorial": ["editorial_family_repeat", "editorial_family_repeat"],
                    "theme": [],
                    "surface": [],
                    "template": ["template_repeat", "template_repeat"],
                },
            }
        },
    )
    repeated = PuzzleCandidate(
        puzzle_id="puzzle_recent_repeat",
        board_words=[f"RR{index}" for index in range(16)],
        groups=[
            group.model_copy(
                update={
                    "words": [f"RR{group_index * 4 + word_index}" for word_index in range(4)],
                    "word_ids": [
                        f"recent_repeat_{group_index}_{word_index}" for word_index in range(4)
                    ],
                }
            )
            for group_index, group in enumerate(dummy_groups)
        ],
        metadata={
            "semantic_majority_board": True,
            "balanced_mixed_board": False,
            "board_family_signature": "board_family_repeat",
            "editorial_family_signature": "editorial_family_repeat",
            "mechanism_template_signature": "template_repeat",
            "theme_family_signatures": [],
            "surface_wordplay_family_signatures": [],
            "ranking_score": 0.97,
        },
    )
    fresh = PuzzleCandidate(
        puzzle_id="puzzle_recent_fresh",
        board_words=[f"RF{index}" for index in range(16)],
        groups=[
            group.model_copy(
                update={
                    "words": [f"RF{group_index * 4 + word_index}" for word_index in range(4)],
                    "word_ids": [
                        f"recent_fresh_{group_index}_{word_index}" for word_index in range(4)
                    ],
                }
            )
            for group_index, group in enumerate(dummy_groups)
        ],
        metadata={
            "semantic_majority_board": True,
            "balanced_mixed_board": False,
            "board_family_signature": "board_family_fresh",
            "editorial_family_signature": "editorial_family_fresh",
            "mechanism_template_signature": "template_fresh",
            "theme_family_signatures": [],
            "surface_wordplay_family_signatures": [],
            "ranking_score": 0.96,
        },
    )
    verification = VerificationResult(
        passed=True,
        decision=VerificationDecision.ACCEPT,
        ambiguity_score=0.08,
        leakage_estimate=0.02,
    )
    repeated_score = PuzzleScore(
        scorer_name="test",
        overall=0.97,
        coherence=0.91,
        ambiguity_penalty=0.08,
        components={},
    )
    fresh_score = PuzzleScore(
        scorer_name="test",
        overall=0.96,
        coherence=0.91,
        ambiguity_penalty=0.08,
        components={},
    )

    repeated_key = PuzzleGenerationPipeline._selection_key(
        repeated,
        verification,
        repeated_score,
        context=context,
        demo_mode=False,
    )
    fresh_key = PuzzleGenerationPipeline._selection_key(
        fresh,
        verification,
        fresh_score,
        context=context,
        demo_mode=False,
    )

    assert fresh_key < repeated_key
