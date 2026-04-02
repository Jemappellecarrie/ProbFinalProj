"""Focused tests for the Stage 3 A+ enhancements."""

from __future__ import annotations

from collections import Counter

from app.core.enums import GenerationMode, GroupType
from app.domain.value_objects import GenerationContext
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.features.semantic_baseline import (
    mean_pairwise_similarity,
    normalize_signal,
    vector_centroid,
)
from app.generators.phonetic import HumanPhoneticGroupGenerator
from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    RejectedPuzzleRecord,
    ScoreBreakdownView,
)
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.scoring.calibration import build_batch_calibration_summary
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.scoring.style_analysis import HumanStyleAnalyzer
from app.solver.mock_solver import MockSolverBackend
from app.solver.verifier import InternalPuzzleVerifier


def _generator_context() -> GenerationContext:
    return GenerationContext(
        request_id="req_stage3",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=GroupType.ordered(),
    )


def _phonetic_entries() -> list[WordEntry]:
    return [
        WordEntry(word_id="word_bake", surface_form="BAKE", normalized="bake"),
        WordEntry(word_id="word_cake", surface_form="CAKE", normalized="cake"),
        WordEntry(word_id="word_lake", surface_form="LAKE", normalized="lake"),
        WordEntry(word_id="word_rake", surface_form="RAKE", normalized="rake"),
        WordEntry(word_id="word_heel", surface_form="HEEL", normalized="heel"),
        WordEntry(word_id="word_keel", surface_form="KEEL", normalized="keel"),
        WordEntry(word_id="word_peel", surface_form="PEEL", normalized="peel"),
        WordEntry(word_id="word_reel", surface_form="REEL", normalized="reel"),
        WordEntry(word_id="word_bash", surface_form="BASH", normalized="bash"),
        WordEntry(word_id="word_cash", surface_form="CASH", normalized="cash"),
        WordEntry(word_id="word_dash", surface_form="DASH", normalized="dash"),
        WordEntry(word_id="word_mash", surface_form="MASH", normalized="mash"),
    ]


def _homophone_entries() -> list[WordEntry]:
    return [
        WordEntry(word_id="word_right", surface_form="RIGHT", normalized="right"),
        WordEntry(word_id="word_write", surface_form="WRITE", normalized="write"),
        WordEntry(word_id="word_rite", surface_form="RITE", normalized="rite"),
        WordEntry(word_id="word_wright", surface_form="WRIGHT", normalized="wright"),
    ]


def _member_specs(
    prefix: str,
    words: list[str],
    sketch: list[float],
    *,
    semantic_tags: list[str] | None = None,
    theme_tags: list[str] | None = None,
    phonetic_signals: list[str] | None = None,
) -> list[tuple[str, str, list[float], list[str], list[str], list[str]]]:
    return [
        (
            word,
            f"{prefix}_{index}",
            list(sketch),
            list(semantic_tags or []),
            list(theme_tags or []),
            list(phonetic_signals or []),
        )
        for index, word in enumerate(words, start=1)
    ]


def _feature(
    word_id: str,
    normalized: str,
    sketch: list[float],
    semantic_tags: list[str],
    theme_tags: list[str],
    phonetic_signals: list[str],
) -> WordFeatures:
    return WordFeatures(
        word_id=word_id,
        normalized=normalized,
        semantic_tags=semantic_tags,
        lexical_signals=[],
        phonetic_signals=phonetic_signals,
        theme_tags=theme_tags,
        extraction_mode="semantic_baseline_v1",
        provenance=["test"],
        debug_attributes={
            "semantic_sketch": sketch,
            "support": {"support_level": "metadata_backed"},
        },
    )


def _build_fixture(kind: str) -> tuple[PuzzleCandidate, GenerationContext]:
    if kind == "bland":
        group_specs = [
            (
                GroupType.SEMANTIC,
                "Planets",
                _member_specs(
                    "planet",
                    ["MERCURY", "VENUS", "EARTH", "MARS"],
                    [1.0, 0.0, 0.0, 0.0],
                    semantic_tags=["planet", "astronomy"],
                ),
                0.94,
                {},
            ),
            (
                GroupType.SEMANTIC,
                "Gemstones",
                _member_specs(
                    "gem",
                    ["RUBY", "OPAL", "JADE", "TOPAZ"],
                    [0.0, 1.0, 0.0, 0.0],
                    semantic_tags=["gemstone", "mineral"],
                ),
                0.93,
                {},
            ),
            (
                GroupType.SEMANTIC,
                "Birds",
                _member_specs(
                    "bird",
                    ["FALCON", "EAGLE", "HAWK", "OWL"],
                    [0.0, 0.0, 1.0, 0.0],
                    semantic_tags=["bird", "airborne"],
                ),
                0.92,
                {},
            ),
            (
                GroupType.SEMANTIC,
                "Fish",
                _member_specs(
                    "fish",
                    ["SALMON", "TROUT", "CARP", "EEL"],
                    [0.0, 0.0, 0.0, 1.0],
                    semantic_tags=["fish", "aquatic"],
                ),
                0.91,
                {},
            ),
        ]
    elif kind == "mixed":
        group_specs = [
            (
                GroupType.SEMANTIC,
                "Planets",
                _member_specs(
                    "planet",
                    ["MERCURY", "VENUS", "EARTH", "MARS"],
                    [1.0, 0.0, 0.0, 0.0],
                    semantic_tags=["planet", "astronomy"],
                ),
                0.94,
                {},
            ),
            (
                GroupType.SEMANTIC,
                "Gemstones",
                _member_specs(
                    "gem",
                    ["RUBY", "OPAL", "JADE", "TOPAZ"],
                    [0.0, 1.0, 0.0, 0.0],
                    semantic_tags=["gemstone", "mineral"],
                ),
                0.93,
                {},
            ),
            (
                GroupType.PHONETIC,
                "Rhymes with -AKE",
                _member_specs(
                    "ake",
                    ["BAKE", "CAKE", "LAKE", "RAKE"],
                    [0.0, 0.0, 1.0, 0.0],
                    phonetic_signals=["rhyme:ake"],
                ),
                0.89,
                {
                    "phonetic_pattern_type": "perfect_rhyme",
                    "normalized_phonetic_signature": "perfect_rhyme:ey1_k",
                    "rule_signature": "phonetic:perfect_rhyme:ey1_k",
                    "spelling_rhyme_hint": "AKE",
                },
            ),
            (
                GroupType.THEME,
                "Pac-Man ghosts",
                _member_specs(
                    "ghost",
                    ["BLINKY", "CLYDE", "INKY", "PINKY"],
                    [0.0, 0.0, 0.0, 1.0],
                    theme_tags=["ghost", "pacman"],
                ),
                0.9,
                {
                    "theme_name": "pac_man_ghosts",
                    "theme_source": "curated_theme_inventory_v1",
                    "rule_signature": "theme:pac_man_ghosts",
                },
            ),
        ]
    elif kind == "reject":
        aircraft_vector = [0.97, 0.243, 0.0, 0.0]
        group_specs = [
            (
                GroupType.SEMANTIC,
                "Birds",
                _member_specs(
                    "bird",
                    ["FALCON", "EAGLE", "HAWK", "OWL"],
                    [1.0, 0.0, 0.0, 0.0],
                    semantic_tags=["bird", "airborne"],
                ),
                0.78,
                {},
            ),
            (
                GroupType.SEMANTIC,
                "Aircraft",
                _member_specs(
                    "air",
                    ["JET", "DRONE", "GLIDER", "ROCKET"],
                    aircraft_vector,
                    semantic_tags=["machine", "airborne"],
                ),
                0.74,
                {},
            ),
            (
                GroupType.SEMANTIC,
                "Trees",
                _member_specs(
                    "tree",
                    ["PINE", "MAPLE", "OAK", "BIRCH"],
                    [0.0, 1.0, 0.0, 0.0],
                    semantic_tags=["tree", "plant"],
                ),
                0.9,
                {},
            ),
            (
                GroupType.PHONETIC,
                "Rhymes with -AKE",
                _member_specs(
                    "ake",
                    ["BAKE", "CAKE", "LAKE", "RAKE"],
                    [0.97, 0.243, 0.0, 0.0],
                    phonetic_signals=["rhyme:ake"],
                ),
                0.86,
                {
                    "phonetic_pattern_type": "perfect_rhyme",
                    "normalized_phonetic_signature": "perfect_rhyme:ey1_k",
                    "rule_signature": "phonetic:perfect_rhyme:ey1_k",
                    "spelling_rhyme_hint": "AKE",
                },
            ),
        ]
    else:
        raise ValueError(f"Unknown fixture kind: {kind}")

    features_by_word_id: dict[str, WordFeatures] = {}
    groups: list[GroupCandidate] = []
    board_words: list[str] = []

    for group_type, label, members, confidence, extra_metadata in group_specs:
        words = [word for word, _, _, _, _, _ in members]
        word_ids = [word_id for _, word_id, _, _, _, _ in members]
        for word, word_id, sketch, semantic_tags, theme_tags, phonetic_signals in members:
            features_by_word_id[word_id] = _feature(
                word_id=word_id,
                normalized=word.lower(),
                sketch=sketch,
                semantic_tags=semantic_tags,
                theme_tags=theme_tags,
                phonetic_signals=phonetic_signals,
            )

        vectors = [
            features_by_word_id[word_id].debug_attributes["semantic_sketch"] for word_id in word_ids
        ]
        shared_signals = sorted(
            set.intersection(
                *[
                    set(features_by_word_id[word_id].semantic_tags)
                    | set(features_by_word_id[word_id].theme_tags)
                    | set(features_by_word_id[word_id].phonetic_signals)
                    for word_id in word_ids
                ]
            )
        )
        metadata = {
            "normalized_label": normalize_signal(label),
            "shared_tags": shared_signals,
            "semantic_centroid": [round(value, 6) for value in vector_centroid(vectors)],
            "mean_pairwise_similarity": round(mean_pairwise_similarity(vectors), 4),
            "evidence": {"shared_signals": shared_signals},
        }
        metadata.update(extra_metadata)
        if group_type is GroupType.PHONETIC:
            metadata["generator_type"] = "phonetic"
            metadata["evidence"].update(
                {
                    "pronunciation_membership": [
                        {"word": word, "word_id": word_id, "shared_rhyme_hint": "AKE"}
                        for word, word_id in zip(words, word_ids, strict=True)
                    ]
                }
            )
        if group_type is GroupType.THEME:
            metadata["evidence"].update(
                {
                    "membership": [
                        {"word": word, "word_id": word_id, "source": "curated_theme_inventory_v1"}
                        for word, word_id in zip(words, word_ids, strict=True)
                    ]
                }
            )

        groups.append(
            GroupCandidate(
                candidate_id=f"group_{normalize_signal(label)}",
                group_type=group_type,
                label=label,
                rationale=f"{label} rationale",
                words=words,
                word_ids=word_ids,
                source_strategy="test",
                extraction_mode="semantic_baseline_v1",
                confidence=confidence,
                metadata=metadata,
            )
        )
        board_words.extend(words)

    puzzle = PuzzleCandidate(
        puzzle_id=f"puzzle_{kind}",
        board_words=board_words,
        groups=groups,
        compatibility_notes=[],
        metadata={
            "mechanism_mix_summary": dict(
                sorted(Counter(group.group_type.value for group in groups).items())
            ),
            "mixed_board": len({group.group_type for group in groups}) > 1,
            "unique_group_type_count": len({group.group_type for group in groups}),
            "ranking_score": 3.0,
        },
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


def _accepted_record(
    puzzle: PuzzleCandidate,
    verification,
    score,
    *,
    iteration_index: int = 0,
) -> AcceptedPuzzleRecord:
    return AcceptedPuzzleRecord(
        iteration_index=iteration_index,
        request_seed=17 + iteration_index,
        puzzle_id=puzzle.puzzle_id,
        board_words=puzzle.board_words,
        group_labels=[group.label for group in puzzle.groups],
        group_types=[group.group_type.value for group in puzzle.groups],
        mechanism_mix_summary=dict(
            sorted(Counter(group.group_type.value for group in puzzle.groups).items())
        ),
        mixed_board=bool(puzzle.metadata.get("mixed_board", False)),
        verification_decision=verification.decision.value,
        score_breakdown=ScoreBreakdownView(
            overall=score.overall,
            coherence=score.coherence,
            ambiguity_penalty=score.ambiguity_penalty,
            human_likeness=score.human_likeness,
            components=score.components,
        ),
        ambiguity_report=verification.ambiguity_report,
        ensemble_result=verification.ensemble_result,
        style_analysis=score.style_analysis,
        selected_components={
            "generators": ["human_semantic_group_generator", "human_phonetic_group_generator"]
        },
    )


def _rejected_record(
    puzzle: PuzzleCandidate,
    verification,
    score,
    *,
    iteration_index: int = 0,
) -> RejectedPuzzleRecord:
    return RejectedPuzzleRecord(
        iteration_index=iteration_index,
        request_seed=31 + iteration_index,
        puzzle_id=puzzle.puzzle_id,
        board_words=puzzle.board_words,
        group_labels=[group.label for group in puzzle.groups],
        group_types=[group.group_type.value for group in puzzle.groups],
        mechanism_mix_summary=dict(
            sorted(Counter(group.group_type.value for group in puzzle.groups).items())
        ),
        mixed_board=bool(puzzle.metadata.get("mixed_board", False)),
        verification_decision=verification.decision.value,
        score_breakdown=ScoreBreakdownView(
            overall=score.overall,
            coherence=score.coherence,
            ambiguity_penalty=score.ambiguity_penalty,
            human_likeness=score.human_likeness,
            components=score.components,
        ),
        reject_reasons=[reason.code.value for reason in verification.reject_reasons],
        ambiguity_report=verification.ambiguity_report,
        ensemble_result=verification.ensemble_result,
        style_analysis=score.style_analysis,
        selected_components={
            "generators": ["human_semantic_group_generator", "human_phonetic_group_generator"]
        },
    )


def test_human_phonetic_generator_emits_evidence_rich_candidates_deterministically() -> None:
    entries = _phonetic_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }
    generator = HumanPhoneticGroupGenerator()

    first = generator.generate(entries, features_by_word_id, _generator_context())
    second = generator.generate(entries, features_by_word_id, _generator_context())

    assert first
    assert [candidate.candidate_id for candidate in first] == [
        candidate.candidate_id for candidate in second
    ]
    assert all(candidate.group_type is GroupType.PHONETIC for candidate in first)

    ake_group = next(
        candidate for candidate in first if set(candidate.words) == {"BAKE", "CAKE", "LAKE", "RAKE"}
    )
    assert ake_group.label == "Rhymes with -AKE"
    assert ake_group.metadata["phonetic_pattern_type"] == "perfect_rhyme"
    assert ake_group.metadata["generator_type"] == "phonetic"
    assert ake_group.metadata["rule_signature"].startswith("phonetic:perfect_rhyme:")
    assert ake_group.metadata["normalized_phonetic_signature"].startswith("perfect_rhyme:")
    assert len(ake_group.metadata["evidence"]["pronunciation_membership"]) == 4
    assert (
        len(
            [
                candidate
                for candidate in first
                if set(candidate.words) == {"BAKE", "CAKE", "LAKE", "RAKE"}
            ]
        )
        == 1
    )


def test_human_phonetic_generator_supports_exact_homophone_groups_with_explicit_evidence() -> None:
    entries = _homophone_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }

    candidates = HumanPhoneticGroupGenerator().generate(
        entries, features_by_word_id, _generator_context()
    )

    assert len(candidates) == 1
    homophone_group = candidates[0]
    assert homophone_group.label == 'Homophones of "RIGHT"'
    assert homophone_group.metadata["phonetic_pattern_type"] == "exact_homophone"
    assert homophone_group.metadata["normalized_phonetic_signature"] == "exact_homophone:r_ay1_t"
    assert homophone_group.metadata["evidence"]["homophone_class"] == "R AY1 T"


def test_style_analyzer_prefers_semantic_majority_to_formulaic_mix() -> None:
    bland_puzzle, bland_context = _build_fixture("bland")
    mixed_puzzle, mixed_context = _build_fixture("mixed")
    verifier = InternalPuzzleVerifier(
        solver=MockSolverBackend(),
        style_analyzer=HumanStyleAnalyzer(),
    )
    analyzer = HumanStyleAnalyzer()

    bland_verification = verifier.verify(bland_puzzle, bland_context)
    mixed_verification = verifier.verify(mixed_puzzle, mixed_context)
    bland_report = analyzer.analyze(bland_puzzle, bland_verification, bland_context)
    mixed_report = analyzer.analyze(mixed_puzzle, mixed_verification, mixed_context)

    assert len(bland_report.group_style_summaries) == 4
    assert bland_report.board_style_summary is not None
    assert bland_report.mechanism_mix_profile is not None
    assert bland_report.style_target_comparison
    assert bland_report.board_style_summary.board_archetype == "semantic_heavy"
    assert "unique_group_type_count_low" not in bland_report.out_of_band_flags

    assert mixed_report.board_style_summary is not None
    assert mixed_report.mechanism_mix_profile is not None
    assert mixed_report.mechanism_mix_profile.counts["phonetic"] == 1
    assert (
        bland_report.board_style_summary.style_alignment_score
        >= mixed_report.board_style_summary.style_alignment_score
    )
    assert mixed_report.board_style_summary.metrics["wordplay_group_count"] == 1.0


def test_batch_calibration_summary_aggregates_style_and_surfaces_target_drift() -> None:
    bland_puzzle, bland_context = _build_fixture("bland")
    reject_puzzle, reject_context = _build_fixture("reject")
    verifier = InternalPuzzleVerifier(
        solver=MockSolverBackend(),
        style_analyzer=HumanStyleAnalyzer(),
    )
    scorer = HumanOwnedPuzzleScorer(style_analyzer=HumanStyleAnalyzer())

    bland_verification = verifier.verify(bland_puzzle, bland_context)
    reject_verification = verifier.verify(reject_puzzle, reject_context)
    bland_score = scorer.score(bland_puzzle, bland_verification, bland_context)
    reject_score = scorer.score(reject_puzzle, reject_verification, reject_context)

    summary = build_batch_calibration_summary(
        accepted_records=[_accepted_record(bland_puzzle, bland_verification, bland_score)],
        rejected_records=[_rejected_record(reject_puzzle, reject_verification, reject_score)],
        top_k_records=[_accepted_record(bland_puzzle, bland_verification, bland_score)],
    )

    assert summary.target_version == "style_targets_v1"
    assert summary.accepted.style_metric_averages["style_alignment_score"] >= 0.0
    assert any(
        comparison.metric_name == "rejected.phonetic_group_count"
        and comparison.within_band is False
        for comparison in summary.target_comparison
    )
    payload = summary.model_dump(mode="json")
    assert payload["top_k"]["out_of_band_flag_counts"]["label_token_mean_low"] >= 1


def test_stage3_style_policy_keeps_formulaic_mixed_boards_demoted() -> None:
    bland_puzzle, bland_context = _build_fixture("bland")
    mixed_puzzle, mixed_context = _build_fixture("mixed")
    reject_puzzle, reject_context = _build_fixture("reject")
    verifier = InternalPuzzleVerifier(
        solver=MockSolverBackend(),
        style_analyzer=HumanStyleAnalyzer(),
    )
    scorer = HumanOwnedPuzzleScorer(style_analyzer=HumanStyleAnalyzer())

    bland_verification = verifier.verify(bland_puzzle, bland_context)
    mixed_verification = verifier.verify(mixed_puzzle, mixed_context)
    reject_verification = verifier.verify(reject_puzzle, reject_context)

    bland_score = scorer.score(bland_puzzle, bland_verification, bland_context)
    mixed_score = scorer.score(mixed_puzzle, mixed_verification, mixed_context)
    reject_score = scorer.score(reject_puzzle, reject_verification, reject_context)

    assert "style_monotony" in bland_verification.warning_flags
    assert "style_monotony" not in mixed_verification.warning_flags
    assert mixed_verification.style_analysis is not None
    assert (
        bland_score.components["style_alignment_bonus"]
        > mixed_score.components["style_alignment_bonus"]
    )
    assert bland_score.overall > reject_score.overall
    assert bland_score.overall > mixed_score.overall
    assert mixed_score.components["surface_wordplay_penalty"] > 0.0
    assert mixed_score.components["microtheme_overuse_penalty"] > 0.0
    assert reject_verification.decision == "reject"


def test_style_analyzer_exposes_label_and_clue_payoff_diagnostics() -> None:
    mixed_puzzle, mixed_context = _build_fixture("mixed")
    verifier = InternalPuzzleVerifier(
        solver=MockSolverBackend(),
        style_analyzer=HumanStyleAnalyzer(),
    )
    analyzer = HumanStyleAnalyzer()

    mixed_verification = verifier.verify(mixed_puzzle, mixed_context)
    report = analyzer.analyze(mixed_puzzle, mixed_verification, mixed_context)

    assert report.board_style_summary is not None
    metrics = report.board_style_summary.metrics
    assert "phrase_template_group_count" in metrics
    assert "phrase_payoff_score" in metrics
    assert "clue_payoff_bonus_applied" in metrics
    assert "surface_wordplay_penalty_applied" in metrics
    assert "low_payoff_pattern_flags" in metrics
    assert "clue_like_label_count" in metrics
    assert "taxonomy_like_label_count" in metrics
    assert "label_polish_applied" in metrics
    assert metrics["surface_wordplay_penalty_applied"] >= 0.0
    assert metrics["low_payoff_pattern_flags"] >= 1.0


def test_style_analyzer_treats_blank_frame_labels_as_more_clue_like_than_taxonomy_like() -> None:
    mixed_puzzle, mixed_context = _build_fixture("mixed")
    polished_groups = []
    for group in mixed_puzzle.groups:
        if group.group_type is GroupType.PHONETIC:
            polished_groups.append(
                group.model_copy(
                    update={
                        "label": "___AKE",
                        "metadata": {
                            **group.metadata,
                            "label_polish_applied": True,
                            "label_polish_reason": "blank_frame_suffix_label",
                        },
                    }
                )
            )
        else:
            polished_groups.append(group)
    polished_puzzle = mixed_puzzle.model_copy(update={"groups": polished_groups})
    verifier = InternalPuzzleVerifier(
        solver=MockSolverBackend(),
        style_analyzer=HumanStyleAnalyzer(),
    )
    analyzer = HumanStyleAnalyzer()

    verification = verifier.verify(polished_puzzle, mixed_context)
    report = analyzer.analyze(polished_puzzle, verification, mixed_context)

    assert report.board_style_summary is not None
    metrics = report.board_style_summary.metrics
    assert metrics["clue_like_label_count"] >= 1.0
    assert metrics["taxonomy_like_label_count"] < 2.0
