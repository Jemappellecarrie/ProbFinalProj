"""Stage 4 release-hardening regression and tooling tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.core.enums import GenerationMode, GroupType
from app.domain.value_objects import GenerationContext
from app.features.semantic_baseline import mean_pairwise_similarity, vector_centroid
from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    BatchEvaluationConfig,
    BatchEvaluationSummary,
    ScoreBreakdownView,
    TopKSummary,
)
from app.schemas.feature_models import WordFeatures
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.services.evaluation_service import EvaluationService
from app.solver.mock_solver import MockSolverBackend
from app.solver.verifier import InternalPuzzleVerifier

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _fixture_payload(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURES_DIR / "regression_boards.json").read_text())
    return payload[name]


def _evaluation_contract() -> dict[str, list[str]]:
    return json.loads((FIXTURES_DIR / "eval_artifact_contract.json").read_text())


def _word_feature(member: dict[str, object]) -> WordFeatures:
    return WordFeatures(
        word_id=str(member["word_id"]),
        normalized=str(member["word"]).lower(),
        semantic_tags=list(member.get("semantic_tags", [])),
        lexical_signals=list(member.get("lexical_signals", [])),
        phonetic_signals=list(member.get("phonetic_signals", [])),
        theme_tags=list(member.get("theme_tags", [])),
        extraction_mode="semantic_baseline_v1",
        provenance=["release_fixture"],
        debug_attributes={
            "semantic_sketch": list(member["vector"]),
            "support": {"support_level": "fixture"},
        },
    )


def _group_metadata(
    group_type: GroupType,
    group: dict[str, object],
    words: list[str],
    word_ids: list[str],
    vectors: list[list[float]],
) -> dict[str, object]:
    shared_tags = list(group.get("shared_tags", []))
    metadata = dict(group.get("metadata", {}))
    evidence = dict(metadata.get("evidence", {}))
    evidence.setdefault("shared_signals", shared_tags)

    if group_type is GroupType.SEMANTIC:
        evidence.setdefault(
            "member_scores",
            [
                {"word": word, "word_id": word_id, "centroid_similarity": 1.0}
                for word, word_id in zip(words, word_ids, strict=True)
            ],
        )
    elif group_type is GroupType.LEXICAL:
        evidence.setdefault(
            "word_matches",
            [
                {"word": word, "word_id": word_id}
                for word, word_id in zip(words, word_ids, strict=True)
            ],
        )
    elif group_type is GroupType.PHONETIC:
        evidence.setdefault(
            "pronunciation_membership",
            [
                {"word": word, "word_id": word_id}
                for word, word_id in zip(words, word_ids, strict=True)
            ],
        )
    elif group_type is GroupType.THEME:
        evidence.setdefault(
            "membership",
            [
                {"word": word, "word_id": word_id}
                for word, word_id in zip(words, word_ids, strict=True)
            ],
        )

    metadata["evidence"] = evidence
    metadata.setdefault("shared_tags", shared_tags)
    metadata.setdefault(
        "semantic_centroid", [round(value, 6) for value in vector_centroid(vectors)]
    )
    metadata.setdefault("mean_pairwise_similarity", round(mean_pairwise_similarity(vectors), 4))
    return metadata


def _build_fixture(name: str) -> tuple[dict[str, object], PuzzleCandidate, GenerationContext]:
    payload = _fixture_payload(name)
    groups: list[GroupCandidate] = []
    board_words: list[str] = []
    features_by_word_id: dict[str, WordFeatures] = {}

    for group in payload["groups"]:
        members = group["members"]
        words = [str(member["word"]) for member in members]
        word_ids = [str(member["word_id"]) for member in members]
        vectors = [list(member["vector"]) for member in members]
        candidate_slug = str(group["label"]).lower().replace(" ", "_")

        for member in members:
            feature = _word_feature(member)
            features_by_word_id[feature.word_id] = feature

        group_type = GroupType(group["group_type"])
        groups.append(
            GroupCandidate(
                candidate_id=f"{name}_{group_type.value}_{candidate_slug}",
                group_type=group_type,
                label=str(group["label"]),
                rationale=f"{group['label']} regression fixture",
                words=words,
                word_ids=word_ids,
                source_strategy="release_fixture",
                extraction_mode="semantic_baseline_v1",
                confidence=float(group["confidence"]),
                metadata=_group_metadata(group_type, group, words, word_ids, vectors),
            )
        )
        board_words.extend(words)

    mechanism_mix = dict(sorted(Counter(group.group_type.value for group in groups).items()))
    puzzle = PuzzleCandidate(
        puzzle_id=f"release_fixture_{name}",
        board_words=board_words,
        groups=groups,
        metadata={
            "mixed_board": len(mechanism_mix) > 1,
            "mechanism_mix_summary": mechanism_mix,
            "ranking_score": float(payload["ranking_score"]),
        },
    )
    context = GenerationContext(
        request_id=f"release_fixture_{name}",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        run_metadata={"features_by_word_id": features_by_word_id},
    )
    return payload, puzzle, context


def _assert_dotted_path(payload: object, dotted_path: str) -> None:
    current: object = payload
    for part in dotted_path.split("."):
        if isinstance(current, list):
            assert part.isdigit(), f"Expected list index before '{part}' in '{dotted_path}'."
            index = int(part)
            assert current, f"Expected non-empty list for '{dotted_path}'."
            assert index < len(current), f"List index {index} missing in '{dotted_path}'."
            current = current[index]
            continue

        assert isinstance(current, dict), f"Expected mapping before '{part}' in '{dotted_path}'."
        assert part in current, f"Missing '{dotted_path}'."
        current = current[part]


@pytest.mark.parametrize(
    "fixture_name",
    ["semantic_accept", "mixed_accept", "phonetic_accept", "borderline", "reject"],
)
def test_curated_board_fixtures_preserve_stage4_decisions(fixture_name: str) -> None:
    payload, puzzle, context = _build_fixture(fixture_name)

    verification = InternalPuzzleVerifier(solver=MockSolverBackend()).verify(puzzle, context)
    score = HumanOwnedPuzzleScorer().score(puzzle, verification, context)

    assert verification.decision.value == payload["expected_decision"]
    assert verification.passed is (payload["expected_decision"] != "reject")
    assert verification.ambiguity_report is not None
    assert verification.ambiguity_report.risk_level.value == payload["expected_risk_level"]
    assert verification.style_analysis is not None
    assert verification.style_analysis.board_style_summary is not None
    assert (
        verification.style_analysis.mechanism_mix_profile.counts
        == payload["expected_mechanism_mix"]
    )
    assert (
        verification.style_analysis.board_style_summary.mechanism_mix_profile.mixed_board
        is payload["expected_mixed_board"]
    )
    assert (
        verification.style_analysis.board_style_summary.board_archetype
        == payload["expected_archetype"]
    )
    assert verification.style_analysis.style_target_comparison
    assert score.style_analysis is not None
    assert "group_coherence" in score.components
    assert "style_alignment_bonus" in score.components

    if verification.passed:
        assert score.overall >= float(payload["minimum_score"])
    else:
        assert verification.reject_reasons


def test_release_fixture_ranking_keeps_accepts_ahead_of_borderline() -> None:
    semantic_payload, semantic_puzzle, semantic_context = _build_fixture("semantic_accept")
    mixed_payload, mixed_puzzle, mixed_context = _build_fixture("mixed_accept")
    borderline_payload, borderline_puzzle, borderline_context = _build_fixture("borderline")

    records: list[AcceptedPuzzleRecord] = []
    for _payload, puzzle, context in [
        (semantic_payload, semantic_puzzle, semantic_context),
        (mixed_payload, mixed_puzzle, mixed_context),
        (borderline_payload, borderline_puzzle, borderline_context),
    ]:
        verification = InternalPuzzleVerifier(solver=MockSolverBackend()).verify(puzzle, context)
        score = HumanOwnedPuzzleScorer().score(puzzle, verification, context)
        records.append(
            AcceptedPuzzleRecord(
                iteration_index=len(records),
                request_seed=17 + len(records),
                puzzle_id=puzzle.puzzle_id,
                board_words=puzzle.board_words,
                group_labels=[group.label for group in puzzle.groups],
                group_types=[group.group_type.value for group in puzzle.groups],
                mechanism_mix_summary=puzzle.metadata["mechanism_mix_summary"],
                mixed_board=bool(puzzle.metadata["mixed_board"]),
                verification_decision=verification.decision.value,
                score_breakdown=ScoreBreakdownView(
                    overall=score.overall,
                    coherence=score.coherence,
                    ambiguity_penalty=score.ambiguity_penalty,
                    human_likeness=score.human_likeness,
                    components=score.components,
                ),
                ambiguity_report=verification.ambiguity_report,
                style_analysis=score.style_analysis,
            )
        )

    top_k = EvaluationService._rank_top_k(records, top_k_size=3)

    assert top_k.ranked_puzzles[0].verification_decision == "accept"
    assert top_k.ranked_puzzles[1].verification_decision == "accept"
    assert top_k.ranked_puzzles[2].verification_decision == "borderline"


def test_evaluation_artifacts_match_release_contract(tmp_path: Path) -> None:
    service = EvaluationService(Settings())
    output_dir = tmp_path / "eval_contract"
    service.evaluate_batch(
        BatchEvaluationConfig(
            num_puzzles=2,
            output_dir=str(output_dir),
            save_traces=True,
            top_k_size=1,
            base_seed=17,
            demo_mode=True,
        )
    )

    contract = _evaluation_contract()
    summary = json.loads((output_dir / "summary.json").read_text())
    accepted = json.loads((output_dir / "accepted.json").read_text())
    rejected = json.loads((output_dir / "rejected.json").read_text())
    top_k = json.loads((output_dir / "top_k.json").read_text())
    traces = json.loads((output_dir / "traces.json").read_text())
    calibration_summary = json.loads((output_dir / "calibration_summary.json").read_text())
    style_summary = json.loads((output_dir / "style_summary.json").read_text())
    mechanism_mix_summary = json.loads((output_dir / "mechanism_mix_summary.json").read_text())
    threshold_diagnostics = json.loads((output_dir / "threshold_diagnostics.json").read_text())

    BatchEvaluationSummary.model_validate(summary)
    TopKSummary.model_validate(top_k)

    assert accepted, "Expected at least one accepted record in the demo artifact contract run."
    assert rejected, "Expected at least one rejected record in the demo artifact contract run."
    assert top_k["ranked_puzzles"], "Expected at least one top-k ranked puzzle."
    assert traces, "Expected at least one trace payload."

    for dotted_path in contract["summary"]:
        _assert_dotted_path(summary, dotted_path)
    for dotted_path in contract["accepted_record"]:
        _assert_dotted_path(accepted[0], dotted_path)
    for dotted_path in contract["rejected_record"]:
        _assert_dotted_path(rejected[0], dotted_path)
    for dotted_path in contract["top_k_record"]:
        _assert_dotted_path(top_k["ranked_puzzles"][0], dotted_path)
    for dotted_path in contract["trace"]:
        _assert_dotted_path(traces[0], dotted_path)
    for dotted_path in contract["calibration_summary_file"]:
        _assert_dotted_path(calibration_summary, dotted_path)
    for dotted_path in contract["style_summary_file"]:
        _assert_dotted_path(style_summary, dotted_path)
    for dotted_path in contract["mechanism_mix_summary_file"]:
        _assert_dotted_path(mechanism_mix_summary, dotted_path)
    for dotted_path in contract["threshold_diagnostics_file"]:
        _assert_dotted_path(threshold_diagnostics, dotted_path)


def test_build_release_summary_script_creates_release_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "release_bundle"
    EvaluationService(Settings(demo_mode=False)).evaluate_batch(
        BatchEvaluationConfig(
            num_puzzles=2,
            output_dir=str(output_dir),
            save_traces=False,
            top_k_size=1,
            base_seed=17,
            demo_mode=False,
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_release_summary.py"),
            "--run-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (output_dir / "release_summary.json").exists()
    assert (output_dir / "release_summary.md").exists()


def test_release_check_script_supports_lightweight_happy_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "release_check"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "release_check.py"),
            "--backend-python",
            sys.executable,
            "--output-dir",
            str(output_dir),
            "--skip-lint",
            "--skip-backend-tests",
            "--skip-frontend",
            "--skip-demo-smoke",
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "CONNECTIONS_DEMO_MODE": "false"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (output_dir / "release_summary.json").exists()
