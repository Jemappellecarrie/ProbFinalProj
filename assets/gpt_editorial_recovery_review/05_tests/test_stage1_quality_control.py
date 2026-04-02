"""Focused tests for the Stage 1 quality-control core."""

from __future__ import annotations

import pytest

from app.core.enums import GenerationMode, GroupType, RejectReasonCode
from app.domain.value_objects import GenerationContext
from app.features.semantic_baseline import mean_pairwise_similarity, vector_centroid
from app.schemas.evaluation_models import (
    AmbiguityRiskLevel,
    EnsembleSolverResult,
    SolverAgreementSummary,
    SolverDisagreementFlag,
)
from app.schemas.feature_models import WordFeatures
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate, SolverResult
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.solver.human_ambiguity_strategy import HumanAmbiguityEvaluator
from app.solver.mock_solver import MockSolverBackend
from app.solver.verifier import InternalPuzzleVerifier


def _feature(
    word_id: str,
    normalized: str,
    sketch: list[float],
    semantic_tags: list[str],
    theme_tags: list[str] | None = None,
) -> WordFeatures:
    return WordFeatures(
        word_id=word_id,
        normalized=normalized,
        semantic_tags=semantic_tags,
        lexical_signals=[],
        phonetic_signals=[],
        theme_tags=theme_tags or [],
        extraction_mode="semantic_baseline_v1",
        provenance=["test"],
        debug_attributes={
            "semantic_sketch": sketch,
            "support": {"support_level": "metadata_backed"},
        },
    )


def _group(
    label: str,
    words: list[str],
    word_ids: list[str],
    confidence: float,
    features_by_word_id: dict[str, WordFeatures],
) -> GroupCandidate:
    vectors = [
        [float(value) for value in features_by_word_id[word_id].debug_attributes["semantic_sketch"]]
        for word_id in word_ids
    ]
    centroid = vector_centroid(vectors)
    shared_signals = sorted(
        set.intersection(
            *[
                set(features_by_word_id[word_id].semantic_tags)
                | set(features_by_word_id[word_id].theme_tags)
                for word_id in word_ids
            ]
        )
    )
    return GroupCandidate(
        candidate_id=f"group_{label.lower().replace(' ', '_')}",
        group_type=GroupType.SEMANTIC,
        label=label,
        rationale=f"{label} rationale",
        words=words,
        word_ids=word_ids,
        source_strategy="test",
        extraction_mode="semantic_baseline_v1",
        confidence=confidence,
        metadata={
            "shared_tags": shared_signals,
            "semantic_centroid": [round(value, 6) for value in centroid],
            "mean_pairwise_similarity": round(mean_pairwise_similarity(vectors), 4),
            "evidence": {
                "shared_signals": shared_signals,
                "member_scores": [
                    {"word": word, "word_id": word_id, "centroid_similarity": 1.0}
                    for word, word_id in zip(words, word_ids, strict=True)
                ],
            },
        },
    )


def _fixture(kind: str) -> tuple[PuzzleCandidate, GenerationContext]:
    if kind == "clear":
        group_specs = [
            (
                "Planets",
                [
                    ("MERCURY", "planet_a", [1.0, 0.0, 0.0, 0.0], ["planet", "astronomy"]),
                    ("VENUS", "planet_b", [1.0, 0.0, 0.0, 0.0], ["planet", "astronomy"]),
                    ("EARTH", "planet_c", [1.0, 0.0, 0.0, 0.0], ["planet", "astronomy"]),
                    ("MARS", "planet_d", [1.0, 0.0, 0.0, 0.0], ["planet", "astronomy"]),
                ],
                0.94,
            ),
            (
                "Gemstones",
                [
                    ("RUBY", "gem_a", [0.0, 1.0, 0.0, 0.0], ["gemstone", "mineral"]),
                    ("OPAL", "gem_b", [0.0, 1.0, 0.0, 0.0], ["gemstone", "mineral"]),
                    ("JADE", "gem_c", [0.0, 1.0, 0.0, 0.0], ["gemstone", "mineral"]),
                    ("TOPAZ", "gem_d", [0.0, 1.0, 0.0, 0.0], ["gemstone", "mineral"]),
                ],
                0.93,
            ),
            (
                "Ghosts",
                [
                    ("BLINKY", "ghost_a", [0.0, 0.0, 1.0, 0.0], ["ghost", "pacman"]),
                    ("INKY", "ghost_b", [0.0, 0.0, 1.0, 0.0], ["ghost", "pacman"]),
                    ("PINKY", "ghost_c", [0.0, 0.0, 1.0, 0.0], ["ghost", "pacman"]),
                    ("CLYDE", "ghost_d", [0.0, 0.0, 1.0, 0.0], ["ghost", "pacman"]),
                ],
                0.92,
            ),
            (
                "Turtles",
                [
                    ("LEONARDO", "tmnt_a", [0.0, 0.0, 0.0, 1.0], ["tmnt", "turtle"]),
                    ("DONATELLO", "tmnt_b", [0.0, 0.0, 0.0, 1.0], ["tmnt", "turtle"]),
                    ("RAPHAEL", "tmnt_c", [0.0, 0.0, 0.0, 1.0], ["tmnt", "turtle"]),
                    ("MICHELANGELO", "tmnt_d", [0.0, 0.0, 0.0, 1.0], ["tmnt", "turtle"]),
                ],
                0.91,
            ),
        ]
    elif kind in {"borderline", "reject"}:
        aircraft_vector = (
            [0.82, 0.572, 0.0, 0.0] if kind == "borderline" else [0.97, 0.243, 0.0, 0.0]
        )
        aircraft_confidence = 0.81 if kind == "borderline" else 0.74
        bird_confidence = 0.85 if kind == "borderline" else 0.78
        group_specs = [
            (
                "Birds",
                [
                    ("FALCON", "bird_a", [1.0, 0.0, 0.0, 0.0], ["bird", "airborne"]),
                    ("EAGLE", "bird_b", [1.0, 0.0, 0.0, 0.0], ["bird", "airborne"]),
                    ("HAWK", "bird_c", [1.0, 0.0, 0.0, 0.0], ["bird", "airborne"]),
                    ("OWL", "bird_d", [1.0, 0.0, 0.0, 0.0], ["bird", "airborne"]),
                ],
                bird_confidence,
            ),
            (
                "Aircraft",
                [
                    ("JET", "air_a", aircraft_vector, ["machine", "airborne"]),
                    ("DRONE", "air_b", aircraft_vector, ["machine", "airborne"]),
                    ("GLIDER", "air_c", aircraft_vector, ["machine", "airborne"]),
                    ("ROCKET", "air_d", aircraft_vector, ["machine", "airborne"]),
                ],
                aircraft_confidence,
            ),
            (
                "Trees",
                [
                    ("PINE", "tree_a", [0.0, 1.0, 0.0, 0.0], ["tree", "plant"]),
                    ("MAPLE", "tree_b", [0.0, 1.0, 0.0, 0.0], ["tree", "plant"]),
                    ("OAK", "tree_c", [0.0, 1.0, 0.0, 0.0], ["tree", "plant"]),
                    ("BIRCH", "tree_d", [0.0, 1.0, 0.0, 0.0], ["tree", "plant"]),
                ],
                0.9,
            ),
            (
                "Fish",
                [
                    ("SALMON", "fish_a", [0.0, 0.0, 1.0, 0.0], ["fish", "aquatic"]),
                    ("TROUT", "fish_b", [0.0, 0.0, 1.0, 0.0], ["fish", "aquatic"]),
                    ("CARP", "fish_c", [0.0, 0.0, 1.0, 0.0], ["fish", "aquatic"]),
                    ("EEL", "fish_d", [0.0, 0.0, 1.0, 0.0], ["fish", "aquatic"]),
                ],
                0.89,
            ),
        ]
    else:
        raise ValueError(f"Unknown fixture kind: {kind}")

    features_by_word_id: dict[str, WordFeatures] = {}
    groups: list[GroupCandidate] = []
    board_words: list[str] = []

    for label, members, confidence in group_specs:
        words = [word for word, _, _, _ in members]
        word_ids = [word_id for _, word_id, _, _ in members]
        for word, word_id, sketch, semantic_tags in members:
            features_by_word_id[word_id] = _feature(
                word_id=word_id,
                normalized=word.lower(),
                sketch=sketch,
                semantic_tags=semantic_tags,
            )
        groups.append(_group(label, words, word_ids, confidence, features_by_word_id))
        board_words.extend(words)

    puzzle = PuzzleCandidate(
        puzzle_id=f"puzzle_{kind}",
        board_words=board_words,
        groups=groups,
        compatibility_notes=[],
        metadata={},
    )
    context = GenerationContext(
        request_id=f"req_{kind}",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        run_metadata={"features_by_word_id": features_by_word_id},
    )
    return puzzle, context


def _solver_result(puzzle: PuzzleCandidate) -> SolverResult:
    return SolverResult(
        backend_name="test_solver_backend",
        solved=True,
        confidence=1.0,
        proposed_groups=[group.words for group in puzzle.groups],
        alternative_groupings_detected=0,
        notes=[],
        raw_output={},
    )


class _DisagreeingEnsemble:
    def solve(self, puzzle: PuzzleCandidate, context: GenerationContext) -> EnsembleSolverResult:
        return EnsembleSolverResult(
            coordinator_name="test_ensemble",
            primary_solver_name="test_solver_backend",
            votes=[],
            agreement_summary=SolverAgreementSummary(
                total_solvers=2,
                matched_target_count=1,
                alternative_solution_count=1,
                agreement_ratio=0.5,
                disagreement_flags=[SolverDisagreementFlag.TARGET_MISMATCH],
                notes=["fixture disagreement"],
            ),
            notes=["fixture disagreement"],
            metadata={},
        )


def test_stage1_ambiguity_report_surfaces_real_evidence_and_excludes_true_groups() -> None:
    puzzle, context = _fixture("reject")

    result = HumanAmbiguityEvaluator().evaluate(puzzle, _solver_result(puzzle), context)

    assert result.ambiguity_report is not None
    assert result.ambiguity_report.risk_level in {
        AmbiguityRiskLevel.HIGH,
        AmbiguityRiskLevel.CRITICAL,
    }
    evidence_dump = result.ambiguity_report.evidence.model_dump(mode="json")
    assert len(evidence_dump.get("group_coherence_summaries", [])) == 4
    assert len(evidence_dump.get("word_fit_summaries", [])) == 16
    assert evidence_dump.get("cross_group_compatibility")
    alternatives = evidence_dump.get("alternative_groupings", [])
    assert alternatives

    true_groups = {frozenset(group.words) for group in puzzle.groups}
    assert all(frozenset(candidate["words"]) not in true_groups for candidate in alternatives)
    assert alternatives[0]["suspicion_score"] >= alternatives[-1]["suspicion_score"]
    assert any("airborne" in candidate["metadata"]["shared_signals"] for candidate in alternatives)

    board_summary = evidence_dump.get("board_summary")
    assert board_summary is not None
    assert board_summary["max_alternative_group_pressure"] > 0.0
    assert "strong_alternative_group" in board_summary["warning_flags"]


def test_stage1_ambiguity_report_keeps_clear_boards_low_risk() -> None:
    puzzle, context = _fixture("clear")

    result = HumanAmbiguityEvaluator().evaluate(puzzle, _solver_result(puzzle), context)

    assert result.ambiguity_report is not None
    assert result.ambiguity_report.risk_level is AmbiguityRiskLevel.LOW
    evidence_dump = result.ambiguity_report.evidence.model_dump(mode="json")
    assert evidence_dump.get("alternative_groupings", []) == []
    assert evidence_dump["board_summary"]["high_leakage_word_count"] == 0
    assert result.ambiguity_score < 0.2


@pytest.mark.parametrize(
    ("fixture_kind", "expected_decision", "expected_passed"),
    [
        ("clear", "accept", True),
        ("borderline", "borderline", True),
        ("reject", "reject", False),
    ],
)
def test_internal_puzzle_verifier_emits_stage1_decisions(
    fixture_kind: str,
    expected_decision: str,
    expected_passed: bool,
) -> None:
    puzzle, context = _fixture(fixture_kind)

    verification = InternalPuzzleVerifier(solver=MockSolverBackend()).verify(puzzle, context)

    assert verification.decision == expected_decision
    assert verification.passed is expected_passed
    assert verification.summary_metrics["board_pressure"] >= 0.0
    assert verification.evidence_refs
    if expected_decision == "reject":
        assert any(
            reason.code is RejectReasonCode.AMBIGUOUS_GROUPING
            for reason in verification.reject_reasons
        )
    elif expected_decision == "borderline":
        assert verification.warning_flags
    else:
        assert verification.reject_reasons == []


def test_human_owned_scorer_uses_stage1_components_and_ranks_clear_boards_higher() -> None:
    clear_puzzle, clear_context = _fixture("clear")
    reject_puzzle, reject_context = _fixture("reject")
    verifier = InternalPuzzleVerifier(solver=MockSolverBackend())

    clear_verification = verifier.verify(clear_puzzle, clear_context)
    reject_verification = verifier.verify(reject_puzzle, reject_context)
    scorer = HumanOwnedPuzzleScorer()

    clear_score = scorer.score(clear_puzzle, clear_verification, clear_context)
    reject_score = scorer.score(reject_puzzle, reject_verification, reject_context)

    assert 0.0 <= clear_score.overall <= 1.0
    assert 0.0 <= reject_score.overall <= 1.0
    assert {
        "group_coherence",
        "board_balance",
        "evidence_quality",
        "ambiguity_penalty",
        "leakage_penalty",
        "alternative_group_penalty",
    } <= set(clear_score.components)
    assert clear_score.overall > reject_score.overall
    assert clear_score.ambiguity_penalty < reject_score.ambiguity_penalty


def test_solver_disagreement_is_diagnostic_only_for_clear_board() -> None:
    puzzle, context = _fixture("clear")

    verification = InternalPuzzleVerifier(
        solver=MockSolverBackend(),
        solver_ensemble=_DisagreeingEnsemble(),
    ).verify(puzzle, context)

    assert "solver_ensemble_disagreement" in verification.warning_flags
    assert verification.decision == "accept"
    assert verification.passed is True
