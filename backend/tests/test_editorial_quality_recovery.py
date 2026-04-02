"""Regression tests for the editorial-quality recovery pass."""

from __future__ import annotations

from app.config.settings import Settings
from app.core.editorial_quality import build_editorial_family_metadata, group_family_signature
from app.core.enums import GroupType, VerificationDecision
from app.domain.value_objects import GenerationContext
from app.pipeline.builder import HumanPuzzleComposer
from app.schemas.evaluation_models import (
    BoardStyleSummary,
    CandidatePoolPuzzleRecord,
    MechanismMixProfile,
    NYTLikenessPlaceholderScore,
    PuzzleArchetypeSummary,
    ScoreBreakdownView,
    StyleAnalysisReport,
)
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate, VerificationResult
from app.scoring.funnel_report import build_funnel_report
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.services.final_quality_acceptance_service import FinalQualityAcceptanceService


def _group(
    *,
    group_type: GroupType,
    label: str,
    words: list[str],
    metadata: dict[str, object],
) -> GroupCandidate:
    return GroupCandidate(
        candidate_id=f"candidate_{group_type.value}_{label.lower().replace(' ', '_')}",
        group_type=group_type,
        label=label,
        rationale=f"{label} rationale",
        words=words,
        word_ids=[f"{label.lower()}_{index}" for index in range(4)],
        source_strategy="test",
        extraction_mode="test_mode",
        confidence=0.9,
        metadata=metadata,
    )


def _puzzle(puzzle_id: str, groups: list[GroupCandidate]) -> PuzzleCandidate:
    return PuzzleCandidate(
        puzzle_id=puzzle_id,
        board_words=[word for group in groups for word in group.words],
        groups=groups,
        compatibility_notes=[],
        metadata={},
    )


def _candidate_record(
    *,
    puzzle_id: str,
    board_words: list[str],
    group_labels: list[str],
    group_word_sets: list[list[str]],
    score: float,
    family_signatures: list[str],
    board_family_signature: str,
    editorial_family_signature: str,
    theme_family_signatures: list[str],
    surface_wordplay_family_signatures: list[str],
    editorial_flags: list[str] | None = None,
) -> CandidatePoolPuzzleRecord:
    return CandidatePoolPuzzleRecord(
        iteration_index=0,
        request_seed=17,
        request_rank=1,
        selected=True,
        puzzle_id=puzzle_id,
        board_words=board_words,
        group_labels=group_labels,
        group_word_sets=group_word_sets,
        group_types=["semantic", "lexical", "phonetic", "theme"],
        mechanism_mix_summary={"semantic": 1, "lexical": 1, "phonetic": 1, "theme": 1},
        mixed_board=True,
        verification_decision="accept",
        score_breakdown=ScoreBreakdownView(
            overall=score,
            coherence=0.82,
            ambiguity_penalty=0.12,
            human_likeness=0.7,
            components={"composer_ranking_score": score},
        ),
        group_family_signatures=family_signatures,
        board_family_signature=board_family_signature,
        editorial_family_signature=editorial_family_signature,
        theme_family_signatures=theme_family_signatures,
        surface_wordplay_family_signatures=surface_wordplay_family_signatures,
        editorial_flags=editorial_flags or [],
        warnings=[],
        selected_components={"generators": ["test_generator"]},
    )


def _style_report(
    *,
    semantic_group_count: int = 1,
    lexical_group_count: int = 1,
    phonetic_group_count: int = 1,
    theme_group_count: int = 1,
    board_archetype: str = "balanced_mixed",
    style_alignment_score: float = 1.0,
    formulaic_mix_score: float,
    editorial_flatness_score: float,
    editorial_payoff_score: float,
    microtheme_smallness: float,
    surface_wordplay_score: float,
    family_repetition_risk: float = 0.0,
    family_saturation: float = 0.0,
    repeated_pattern_family_score: float = 0.0,
    wordplay_group_count: float | None = None,
) -> StyleAnalysisReport:
    resolved_wordplay_group_count = (
        wordplay_group_count
        if wordplay_group_count is not None
        else float(lexical_group_count + phonetic_group_count)
    )
    unique_group_type_count = sum(
        1
        for count in (
            semantic_group_count,
            lexical_group_count,
            phonetic_group_count,
            theme_group_count,
        )
        if count > 0
    )
    mix = MechanismMixProfile(
        counts={
            key: value
            for key, value in {
                "semantic": semantic_group_count,
                "lexical": lexical_group_count,
                "phonetic": phonetic_group_count,
                "theme": theme_group_count,
            }.items()
            if value > 0
        },
        shares={
            key: round(value / 4.0, 4)
            for key, value in {
                "semantic": semantic_group_count,
                "lexical": lexical_group_count,
                "phonetic": phonetic_group_count,
                "theme": theme_group_count,
            }.items()
            if value > 0
        },
        unique_group_type_count=unique_group_type_count,
        semantic_group_count=semantic_group_count,
        lexical_group_count=lexical_group_count,
        phonetic_group_count=phonetic_group_count,
        theme_group_count=theme_group_count,
        wordplay_group_count=int(resolved_wordplay_group_count),
        mixed_board=unique_group_type_count > 1,
    )
    metrics = {
        "unique_group_type_count": float(unique_group_type_count),
        "semantic_group_count": float(semantic_group_count),
        "lexical_group_count": float(lexical_group_count),
        "phonetic_group_count": float(phonetic_group_count),
        "theme_group_count": float(theme_group_count),
        "wordplay_group_count": float(resolved_wordplay_group_count),
        "style_alignment_score": style_alignment_score,
        "formulaic_mix_score": formulaic_mix_score,
        "editorial_flatness_score": editorial_flatness_score,
        "editorial_payoff_score": editorial_payoff_score,
        "microtheme_smallness": microtheme_smallness,
        "surface_wordplay_score": surface_wordplay_score,
        "family_repetition_risk": family_repetition_risk,
        "family_saturation": family_saturation,
        "label_naturalness_score": 0.82,
        "earned_wordplay_score": 0.75,
        "repeated_pattern_family_score": repeated_pattern_family_score,
    }
    return StyleAnalysisReport(
        analyzer_name="test_style",
        archetype=PuzzleArchetypeSummary(
            label=board_archetype,
            rationale="fixture",
            flags=[],
        ),
        nyt_likeness=NYTLikenessPlaceholderScore(score=style_alignment_score, notes=[]),
        signals=[],
        group_style_summaries=[],
        board_style_summary=BoardStyleSummary(
            board_archetype=board_archetype,
            mechanism_mix_profile=mix,
            group_archetypes=[],
            label_token_mean=2.0,
            label_token_std=0.2,
            label_consistency=0.9,
            evidence_interpretability=0.8,
            semantic_wordplay_balance=0.66,
            archetype_diversity=1.0,
            redundancy_score=0.1,
            monotony_score=0.0,
            coherence_trickiness_balance=0.8,
            style_alignment_score=style_alignment_score,
            metrics=metrics,
            out_of_band_flags=[],
            notes=[],
        ),
        mechanism_mix_profile=mix,
        style_target_comparison=[],
        out_of_band_flags=[],
        notes=[],
        metadata={},
    )


class _StubStyleAnalyzer:
    def __init__(self, reports: dict[str, StyleAnalysisReport]) -> None:
        self._reports = reports

    def analyze(self, puzzle, verification, context):
        return self._reports[puzzle.puzzle_id]


def _run_state(
    *,
    retention_counts: dict[str, dict[str, int]] | None = None,
) -> dict[str, object]:
    return {
        "family_proposal_count_by_run": {},
        "family_retention_count_by_run": retention_counts or {},
        "family_suppression_events": {},
        "per_family_cap_hits": {},
    }


def test_family_signatures_are_deterministic_and_collapse_board_variants() -> None:
    semantic_a = _group(
        group_type=GroupType.SEMANTIC,
        label="Gemstones",
        words=["RUBY", "OPAL", "JADE", "TOPAZ"],
        metadata={
            "normalized_label": "gemstones",
            "rule_signature": "semantic:gemstone",
            "shared_tags": ["gemstone"],
        },
    )
    semantic_b = _group(
        group_type=GroupType.SEMANTIC,
        label="Gemstones",
        words=["AMBER", "PEARL", "ONYX", "QUARTZ"],
        metadata={
            "normalized_label": "gemstones",
            "rule_signature": "semantic:gemstone",
            "shared_tags": ["gemstone"],
        },
    )
    lexical = _group(
        group_type=GroupType.LEXICAL,
        label="Ends with -AKE",
        words=["BAKE", "CAKE", "LAKE", "MAKE"],
        metadata={
            "normalized_label": "ends_with_ake",
            "pattern_type": "shared_suffix",
            "normalized_pattern": "ake",
            "rule_signature": "lexical:shared_suffix:ake",
        },
    )
    phonetic = _group(
        group_type=GroupType.PHONETIC,
        label="Rhymes with -ASH",
        words=["CASH", "DASH", "GNASH", "MASH"],
        metadata={
            "normalized_label": "rhymes_with_ash",
            "phonetic_pattern_type": "perfect_rhyme",
            "normalized_phonetic_signature": "perfect_rhyme:ae1_sh",
            "rule_signature": "phonetic:perfect_rhyme:ae1_sh",
        },
    )
    theme = _group(
        group_type=GroupType.THEME,
        label="Planets",
        words=["EARTH", "MARS", "MERCURY", "VENUS"],
        metadata={
            "normalized_label": "planets",
            "theme_name": "classical_planets",
            "rule_signature": "theme:classical_planets",
        },
    )

    puzzle_a = _puzzle("puzzle_a", [semantic_a, lexical, phonetic, theme])
    puzzle_b = _puzzle("puzzle_b", [semantic_b, lexical, phonetic, theme])

    lexical_signature = group_family_signature(lexical)
    meta_a = build_editorial_family_metadata(puzzle_a.groups)
    meta_b = build_editorial_family_metadata(puzzle_b.groups)

    assert lexical_signature == "lexical:shared_suffix:ake"
    assert meta_a["board_family_signature"] == meta_b["board_family_signature"]
    assert meta_a["editorial_family_signature"] == meta_b["editorial_family_signature"]
    assert "formulaic_mixed_template" in meta_a["editorial_flags"]


def test_top_review_selection_suppresses_repeated_editorial_families() -> None:
    service = FinalQualityAcceptanceService(Settings(demo_mode=False))
    repeated_family = [
        "semantic:gemstone",
        "lexical:shared_suffix:ake",
        "phonetic:perfect_rhyme:ae1_sh",
        "theme:classical_planets",
    ]
    alternative_family = [
        "semantic:tool",
        "lexical:shared_prefix:sn",
        "phonetic:exact_homophone:eel",
        "theme:common_gemstones",
    ]
    records = [
        _candidate_record(
            puzzle_id="formulaic_1",
            board_words=[f"A{index}" for index in range(16)],
            group_labels=["Gemstones", "Ends with -AKE", "Rhymes with -ASH", "Planets"],
            group_word_sets=[
                ["A0", "A1", "A2", "A3"],
                ["A4", "A5", "A6", "A7"],
                ["A8", "A9", "A10", "A11"],
                ["A12", "A13", "A14", "A15"],
            ],
            score=0.96,
            family_signatures=repeated_family,
            board_family_signature="board_family_formulaic",
            editorial_family_signature="editorial_family_formulaic",
            theme_family_signatures=["theme:classical_planets"],
            surface_wordplay_family_signatures=[
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
            ],
            editorial_flags=["formulaic_mixed_template"],
        ),
        _candidate_record(
            puzzle_id="formulaic_2",
            board_words=[f"B{index}" for index in range(16)],
            group_labels=["Gemstones", "Ends with -AKE", "Rhymes with -ASH", "Planets"],
            group_word_sets=[
                ["B0", "B1", "B2", "B3"],
                ["B4", "B5", "B6", "B7"],
                ["B8", "B9", "B10", "B11"],
                ["B12", "B13", "B14", "B15"],
            ],
            score=0.95,
            family_signatures=repeated_family,
            board_family_signature="board_family_formulaic_variant",
            editorial_family_signature="editorial_family_formulaic",
            theme_family_signatures=["theme:classical_planets"],
            surface_wordplay_family_signatures=[
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
            ],
            editorial_flags=["formulaic_mixed_template"],
        ),
        _candidate_record(
            puzzle_id="stronger_1",
            board_words=[f"C{index}" for index in range(16)],
            group_labels=["Tools", "Starts with SN", "Sounds like EEL", "Gemstones"],
            group_word_sets=[
                ["C0", "C1", "C2", "C3"],
                ["C4", "C5", "C6", "C7"],
                ["C8", "C9", "C10", "C11"],
                ["C12", "C13", "C14", "C15"],
            ],
            score=0.94,
            family_signatures=alternative_family,
            board_family_signature="board_family_stronger_1",
            editorial_family_signature="editorial_family_stronger_1",
            theme_family_signatures=["theme:common_gemstones"],
            surface_wordplay_family_signatures=[
                "lexical:shared_prefix:sn",
                "phonetic:exact_homophone:eel",
            ],
        ),
        _candidate_record(
            puzzle_id="stronger_2",
            board_words=[f"D{index}" for index in range(16)],
            group_labels=["Birds", "Contains ING", "Rhymes with OON", "Planets"],
            group_word_sets=[
                ["D0", "D1", "D2", "D3"],
                ["D4", "D5", "D6", "D7"],
                ["D8", "D9", "D10", "D11"],
                ["D12", "D13", "D14", "D15"],
            ],
            score=0.93,
            family_signatures=[
                "semantic:bird",
                "lexical:shared_substring:ing",
                "phonetic:perfect_rhyme:uwn",
                "theme:classical_planets",
            ],
            board_family_signature="board_family_stronger_2",
            editorial_family_signature="editorial_family_stronger_2",
            theme_family_signatures=["theme:classical_planets"],
            surface_wordplay_family_signatures=[
                "lexical:shared_substring:ing",
                "phonetic:perfect_rhyme:uwn",
            ],
        ),
    ]

    top_k, selected = service._rank_top_review_candidates(records, top_k_size=3)

    assert [record.puzzle_id for record in selected] == [
        "formulaic_1",
        "stronger_1",
        "stronger_2",
    ]
    assert all(
        ranked.editorial_family_signature != "editorial_family_formulaic"
        or ranked.puzzle_id == "formulaic_1"
        for ranked in top_k.ranked_puzzles
    )


def test_candidate_pool_suppresses_repeated_surface_families_before_trimming() -> None:
    composer = HumanPuzzleComposer()
    repeated_suffix_a = _group(
        group_type=GroupType.LEXICAL,
        label="Ends with -AKE",
        words=["BAKE", "CAKE", "LAKE", "MAKE"],
        metadata={
            "pattern_type": "shared_suffix",
            "normalized_pattern": "ake",
            "rule_signature": "lexical:shared_suffix:ake",
        },
    )
    repeated_suffix_b = _group(
        group_type=GroupType.LEXICAL,
        label="Ends with -AKE",
        words=["FAKE", "RAKE", "SAKE", "TAKE"],
        metadata={
            "pattern_type": "shared_suffix",
            "normalized_pattern": "ake",
            "rule_signature": "lexical:shared_suffix:ake",
        },
    )
    fresh_prefix = _group(
        group_type=GroupType.LEXICAL,
        label="Starts with SN",
        words=["SNAG", "SNAP", "SNIP", "SNOW"],
        metadata={
            "pattern_type": "shared_prefix",
            "normalized_pattern": "sn",
            "rule_signature": "lexical:shared_prefix:sn",
        },
    )
    context = GenerationContext(
        request_id="req_pool",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=[GroupType.LEXICAL],
        run_metadata={
            "editorial_run_state": _run_state(
                retention_counts={
                    "group": {"lexical:shared_suffix:ake": 2},
                    "surface": {"lexical:shared_suffix:ake": 2},
                }
            )
        },
    )

    pool, counts = composer._candidate_pool(
        {GroupType.LEXICAL.value: [repeated_suffix_a, repeated_suffix_b, fresh_prefix]},
        context,
    )

    assert counts[GroupType.LEXICAL.value] == 3
    assert [candidate.label for candidate in pool[:2]] == ["Starts with SN", "Ends with -AKE"]


def test_candidate_pool_uses_seed_tiebreaks_to_explore_alternative_families() -> None:
    composer = HumanPuzzleComposer()
    lexical_a = _group(
        group_type=GroupType.LEXICAL,
        label="Starts with SN",
        words=["SNAG", "SNAP", "SNIP", "SNOW"],
        metadata={
            "pattern_type": "shared_prefix",
            "normalized_pattern": "sn",
            "rule_signature": "lexical:shared_prefix:sn",
        },
    )
    lexical_b = _group(
        group_type=GroupType.LEXICAL,
        label="Ends with -AKE",
        words=["BAKE", "CAKE", "LAKE", "MAKE"],
        metadata={
            "pattern_type": "shared_suffix",
            "normalized_pattern": "ake",
            "rule_signature": "lexical:shared_suffix:ake",
        },
    )
    context_a = GenerationContext(
        request_id="req_seed_17",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=[GroupType.LEXICAL],
        run_metadata={"editorial_run_state": _run_state()},
    )
    context_b = GenerationContext(
        request_id="req_seed_18",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=18,
        requested_group_types=[GroupType.LEXICAL],
        run_metadata={"editorial_run_state": _run_state()},
    )

    pool_a, _ = composer._candidate_pool(
        {GroupType.LEXICAL.value: [lexical_a, lexical_b]},
        context_a,
    )
    pool_b, _ = composer._candidate_pool(
        {GroupType.LEXICAL.value: [lexical_a, lexical_b]},
        context_b,
    )

    assert pool_a[0].candidate_id != pool_b[0].candidate_id


def test_human_puzzle_composer_prefers_semantic_majority_board_over_formulaic_mixed_board() -> None:
    composer = HumanPuzzleComposer()
    groups_by_type = {
        GroupType.SEMANTIC.value: [
            _group(
                group_type=GroupType.SEMANTIC,
                label="Planets",
                words=["MERCURY", "VENUS", "EARTH", "MARS"],
                metadata={"rule_signature": "semantic:planet"},
            ),
            _group(
                group_type=GroupType.SEMANTIC,
                label="Gemstones",
                words=["RUBY", "OPAL", "JADE", "TOPAZ"],
                metadata={"rule_signature": "semantic:gemstone"},
            ),
            _group(
                group_type=GroupType.SEMANTIC,
                label="Birds",
                words=["EAGLE", "HAWK", "OWL", "RAVEN"],
                metadata={"rule_signature": "semantic:bird"},
            ),
            _group(
                group_type=GroupType.SEMANTIC,
                label="Tools",
                words=["DRILL", "HAMMER", "SAW", "VISE"],
                metadata={"rule_signature": "semantic:tool"},
            ),
        ],
        GroupType.LEXICAL.value: [
            _group(
                group_type=GroupType.LEXICAL,
                label="Ends with -AKE",
                words=["BAKE", "CAKE", "LAKE", "MAKE"],
                metadata={
                    "pattern_type": "shared_suffix",
                    "normalized_pattern": "ake",
                    "rule_signature": "lexical:shared_suffix:ake",
                },
            )
        ],
        GroupType.PHONETIC.value: [
            _group(
                group_type=GroupType.PHONETIC,
                label="Rhymes with -ASH",
                words=["BASH", "CASH", "DASH", "MASH"],
                metadata={
                    "phonetic_pattern_type": "perfect_rhyme",
                    "normalized_phonetic_signature": "perfect_rhyme:ae1_sh",
                    "rule_signature": "phonetic:perfect_rhyme:ae1_sh",
                },
            )
        ],
        GroupType.THEME.value: [
            _group(
                group_type=GroupType.THEME,
                label="Pac-Man ghosts",
                words=["BLINKY", "CLYDE", "INKY", "PINKY"],
                metadata={
                    "theme_name": "pac_man_ghosts",
                    "rule_signature": "theme:pac_man_ghosts",
                },
            )
        ],
    }
    context = GenerationContext(
        request_id="req_semantic_majority",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
    )

    puzzles = composer.compose(groups_by_type, context)

    assert puzzles
    assert puzzles[0].metadata["semantic_group_count"] >= 3


def test_build_funnel_report_exposes_family_level_metrics() -> None:
    candidates = [
        _candidate_record(
            puzzle_id="formulaic_1",
            board_words=[f"A{index}" for index in range(16)],
            group_labels=["Gemstones", "Ends with -AKE", "Rhymes with -ASH", "Planets"],
            group_word_sets=[
                ["A0", "A1", "A2", "A3"],
                ["A4", "A5", "A6", "A7"],
                ["A8", "A9", "A10", "A11"],
                ["A12", "A13", "A14", "A15"],
            ],
            score=0.96,
            family_signatures=[
                "semantic:gemstone",
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
                "theme:classical_planets",
            ],
            board_family_signature="board_family_formulaic",
            editorial_family_signature="editorial_family_formulaic",
            theme_family_signatures=["theme:classical_planets"],
            surface_wordplay_family_signatures=[
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
            ],
            editorial_flags=["formulaic_mixed_template"],
        ),
        _candidate_record(
            puzzle_id="formulaic_2",
            board_words=[f"B{index}" for index in range(16)],
            group_labels=["Gemstones", "Ends with -AKE", "Rhymes with -ASH", "Planets"],
            group_word_sets=[
                ["B0", "B1", "B2", "B3"],
                ["B4", "B5", "B6", "B7"],
                ["B8", "B9", "B10", "B11"],
                ["B12", "B13", "B14", "B15"],
            ],
            score=0.95,
            family_signatures=[
                "semantic:gemstone",
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
                "theme:classical_planets",
            ],
            board_family_signature="board_family_formulaic_variant",
            editorial_family_signature="editorial_family_formulaic",
            theme_family_signatures=["theme:classical_planets"],
            surface_wordplay_family_signatures=[
                "lexical:shared_suffix:ake",
                "phonetic:perfect_rhyme:ae1_sh",
            ],
            editorial_flags=["formulaic_mixed_template"],
        ),
        _candidate_record(
            puzzle_id="stronger_1",
            board_words=[f"C{index}" for index in range(16)],
            group_labels=["Tools", "Starts with SN", "Sounds like EEL", "Gemstones"],
            group_word_sets=[
                ["C0", "C1", "C2", "C3"],
                ["C4", "C5", "C6", "C7"],
                ["C8", "C9", "C10", "C11"],
                ["C12", "C13", "C14", "C15"],
            ],
            score=0.94,
            family_signatures=[
                "semantic:tool",
                "lexical:shared_prefix:sn",
                "phonetic:exact_homophone:eel",
                "theme:common_gemstones",
            ],
            board_family_signature="board_family_stronger_1",
            editorial_family_signature="editorial_family_stronger_1",
            theme_family_signatures=["theme:common_gemstones"],
            surface_wordplay_family_signatures=[
                "lexical:shared_prefix:sn",
                "phonetic:exact_homophone:eel",
            ],
        ),
    ]
    report = build_funnel_report(
        total_generation_requests=3,
        candidate_records=candidates,
        top_review_candidates=candidates[:2],
        request_diagnostics=[],
    )

    assert report["unique_family_count"] == 2
    assert report["top_k_unique_family_count"] == 1
    assert report["family_repetition_histogram"]["editorial_family_formulaic"] == 2
    assert report["repeated_theme_family_count"] == 1
    assert report["repeated_surface_wordplay_family_count"] >= 1
    assert report["formulaic_board_rate"] == 0.6667
    assert report["repeated_family_rate"] == 0.6667
    assert report["selected_unique_family_count"] == 2
    assert report["winner_family_histogram"]["editorial_family_formulaic"] == 2
    assert report["winner_family_repetition_rate"] == 0.6667
    assert report["winner_mechanism_mix_distribution"]["lexical+phonetic+semantic+theme"] == 3
    assert report["balanced_mixed_winner_rate"] == 1.0
    assert report["winner_microtheme_family_count"] == 2
    assert report["winner_surface_wordplay_rate"] == 1.0
    assert report["winner_semantic_group_count_mean"] == 1.0
    assert "semantic_majority_board_rate" in report
    assert "semantic_majority_winner_rate" in report
    assert "balanced_mixed_board_rate" in report
    assert "surface_wordplay_board_rate" in report
    assert "microtheme_plus_wordplay_cooccurrence_rate" in report
    assert "top_k_microtheme_family_count" in report
    assert "microtheme_family_suppression_events" in report
    assert "family_proposal_count_by_run" in report
    assert "family_retention_count_by_run" in report
    assert "family_suppression_events" in report
    assert "per_family_cap_hits" in report


def test_composer_caps_repeated_small_microtheme_families_after_first_hit() -> None:
    composer = HumanPuzzleComposer()
    groups = [
        _group(
            group_type=GroupType.SEMANTIC,
            label="Planets",
            words=["MERCURY", "VENUS", "EARTH", "MARS"],
            metadata={"rule_signature": "semantic:planet"},
        ),
        _group(
            group_type=GroupType.SEMANTIC,
            label="Birds",
            words=["EAGLE", "HAWK", "OWL", "RAVEN"],
            metadata={"rule_signature": "semantic:bird"},
        ),
        _group(
            group_type=GroupType.LEXICAL,
            label="Ends with -AKE",
            words=["BAKE", "CAKE", "LAKE", "MAKE"],
            metadata={
                "pattern_type": "shared_suffix",
                "normalized_pattern": "ake",
                "rule_signature": "lexical:shared_suffix:ake",
            },
        ),
        _group(
            group_type=GroupType.THEME,
            label="Pac-Man ghosts",
            words=["BLINKY", "CLYDE", "INKY", "PINKY"],
            metadata={
                "theme_name": "pac_man_ghosts",
                "rule_signature": "theme:pac_man_ghosts",
            },
        ),
    ]
    puzzle = _puzzle("microtheme_repeat", groups)
    puzzle.metadata.update(build_editorial_family_metadata(puzzle.groups))

    allowed, reason, signature = composer._family_diversity_allowed(
        puzzle,
        [],
        run_state=_run_state(
            retention_counts={
                "theme": {"theme:pac_man_ghosts": 1},
            }
        ),
    )

    assert allowed is False
    assert reason == "run_small_theme_family_cap"
    assert signature == "theme:pac_man_ghosts"


def test_human_puzzle_composer_polishes_pattern_labels_conservatively() -> None:
    composer = HumanPuzzleComposer()
    groups_by_type = {
        GroupType.SEMANTIC.value: [
            _group(
                group_type=GroupType.SEMANTIC,
                label="Planets",
                words=["MERCURY", "VENUS", "EARTH", "MARS"],
                metadata={"rule_signature": "semantic:planet"},
            )
        ],
        GroupType.LEXICAL.value: [
            _group(
                group_type=GroupType.LEXICAL,
                label="Ends with -AKE",
                words=["BAKE", "CAKE", "LAKE", "MAKE"],
                metadata={
                    "pattern_type": "shared_suffix",
                    "normalized_pattern": "ake",
                    "rule_signature": "lexical:shared_suffix:ake",
                },
            )
        ],
        GroupType.PHONETIC.value: [
            _group(
                group_type=GroupType.PHONETIC,
                label="Rhymes with -ASH",
                words=["BASH", "CASH", "DASH", "MASH"],
                metadata={
                    "phonetic_pattern_type": "perfect_rhyme",
                    "normalized_phonetic_signature": "perfect_rhyme:ae1_sh",
                    "spelling_rhyme_hint": "ASH",
                    "rule_signature": "phonetic:perfect_rhyme:ae1_sh",
                },
            )
        ],
        GroupType.THEME.value: [
            _group(
                group_type=GroupType.THEME,
                label="Pac-Man ghosts",
                words=["BLINKY", "CLYDE", "INKY", "PINKY"],
                metadata={
                    "theme_name": "pac_man_ghosts",
                    "rule_signature": "theme:pac_man_ghosts",
                },
            )
        ],
    }
    context = GenerationContext(
        request_id="req_label_polish",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=GroupType.ordered(),
    )

    puzzles = composer.compose(groups_by_type, context)

    assert puzzles
    labels = {group.label for group in puzzles[0].groups}
    assert "___AKE" in labels
    assert "___ASH" in labels


def test_human_owned_scorer_penalizes_formulaic_presence_only_mix() -> None:
    formulaic_groups = [
        _group(
            group_type=GroupType.SEMANTIC,
            label="Category One",
            words=["A1", "A2", "A3", "A4"],
            metadata={},
        ),
        _group(
            group_type=GroupType.SEMANTIC,
            label="Category Two",
            words=["B1", "B2", "B3", "B4"],
            metadata={},
        ),
        _group(
            group_type=GroupType.SEMANTIC,
            label="Category Three",
            words=["C1", "C2", "C3", "C4"],
            metadata={},
        ),
        _group(
            group_type=GroupType.SEMANTIC,
            label="Category Four",
            words=["D1", "D2", "D3", "D4"],
            metadata={},
        ),
    ]
    formulaic_puzzle = _puzzle("formulaic_board", formulaic_groups)
    stronger_puzzle = _puzzle("strong_board", formulaic_groups)
    context = GenerationContext(
        request_id="req_editorial",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
    )
    verification = VerificationResult(
        passed=True,
        decision=VerificationDecision.ACCEPT,
        leakage_estimate=0.05,
        ambiguity_score=0.1,
    )
    scorer = HumanOwnedPuzzleScorer(
        style_analyzer=_StubStyleAnalyzer(
            {
                "formulaic_board": _style_report(
                    formulaic_mix_score=0.95,
                    editorial_flatness_score=0.85,
                    editorial_payoff_score=0.2,
                    microtheme_smallness=0.8,
                    surface_wordplay_score=0.95,
                ),
                "strong_board": _style_report(
                    formulaic_mix_score=0.15,
                    editorial_flatness_score=0.1,
                    editorial_payoff_score=0.82,
                    microtheme_smallness=0.05,
                    surface_wordplay_score=0.2,
                ),
            }
        )
    )

    formulaic_score = scorer.score(formulaic_puzzle, verification, context)
    strong_score = scorer.score(stronger_puzzle, verification, context)

    assert formulaic_score.overall < strong_score.overall
    assert "formulaic_mix_penalty" in formulaic_score.components
    assert "editorial_payoff_bonus" in strong_score.components


def test_human_owned_scorer_applies_repeated_surface_and_family_saturation_penalties() -> None:
    puzzle = _puzzle(
        "surface_repeat_board",
        [
            _group(
                group_type=GroupType.SEMANTIC,
                label="Planets",
                words=["MERCURY", "VENUS", "EARTH", "MARS"],
                metadata={},
            ),
            _group(
                group_type=GroupType.SEMANTIC,
                label="Gemstones",
                words=["RUBY", "OPAL", "JADE", "TOPAZ"],
                metadata={},
            ),
            _group(
                group_type=GroupType.SEMANTIC,
                label="Birds",
                words=["EAGLE", "HAWK", "OWL", "RAVEN"],
                metadata={},
            ),
            _group(
                group_type=GroupType.SEMANTIC,
                label="Tools",
                words=["DRILL", "HAMMER", "SAW", "VISE"],
                metadata={},
            ),
        ],
    )
    context = GenerationContext(
        request_id="req_surface_repeat",
        mode="human_mixed",
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
    )
    verification = VerificationResult(
        passed=True,
        decision=VerificationDecision.ACCEPT,
        leakage_estimate=0.05,
        ambiguity_score=0.1,
    )
    scorer = HumanOwnedPuzzleScorer(
        style_analyzer=_StubStyleAnalyzer(
            {
                "surface_repeat_board": _style_report(
                    semantic_group_count=1,
                    lexical_group_count=1,
                    phonetic_group_count=1,
                    theme_group_count=1,
                    board_archetype="balanced_mixed",
                    style_alignment_score=0.9,
                    formulaic_mix_score=0.82,
                    editorial_flatness_score=0.74,
                    editorial_payoff_score=0.62,
                    microtheme_smallness=0.72,
                    surface_wordplay_score=0.93,
                    family_repetition_risk=0.88,
                    family_saturation=0.86,
                    repeated_pattern_family_score=0.7,
                ),
            }
        )
    )

    score = scorer.score(puzzle, verification, context)

    assert "repeated_surface_wordplay_penalty" in score.components
    assert "family_saturation_penalty" in score.components
    assert score.components["repeated_surface_wordplay_penalty"] > 0.0
    assert score.components["family_saturation_penalty"] > 0.0
