"""Stage 2 generator-diversity tests."""

from __future__ import annotations

from app.core.enums import GenerationMode, GroupType
from app.domain.value_objects import GenerationContext
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.features.semantic_baseline import mean_pairwise_similarity, vector_centroid
from app.generators.lexical import HumanLexicalGroupGenerator
from app.generators.semantic import HumanSemanticGroupGenerator
from app.generators.theme import HumanThemeGroupGenerator
from app.pipeline.builder import HumanPuzzleComposer
from app.schemas.feature_models import WordEntry
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.solver.mock_solver import MockSolverBackend
from app.solver.verifier import InternalPuzzleVerifier


def _stage2_seed_entries() -> list[WordEntry]:
    return [
        WordEntry(
            word_id="word_mercury",
            surface_form="MERCURY",
            normalized="mercury",
            known_group_hints={"semantic": "planets"},
            metadata={"semantic_tags": ["planet", "astronomy"]},
        ),
        WordEntry(
            word_id="word_venus",
            surface_form="VENUS",
            normalized="venus",
            known_group_hints={"semantic": "planets"},
            metadata={"semantic_tags": ["planet", "astronomy"]},
        ),
        WordEntry(
            word_id="word_earth",
            surface_form="EARTH",
            normalized="earth",
            known_group_hints={"semantic": "planets"},
            metadata={"semantic_tags": ["planet", "astronomy"]},
        ),
        WordEntry(
            word_id="word_mars",
            surface_form="MARS",
            normalized="mars",
            known_group_hints={"semantic": "planets"},
            metadata={"semantic_tags": ["planet", "astronomy"]},
        ),
        WordEntry(
            word_id="word_snap",
            surface_form="SNAP",
            normalized="snap",
            known_group_hints={"lexical": "starts_with_sn"},
            metadata={"lexical_signals": ["prefix:sn"]},
        ),
        WordEntry(
            word_id="word_snip",
            surface_form="SNIP",
            normalized="snip",
            known_group_hints={"lexical": "starts_with_sn"},
            metadata={"lexical_signals": ["prefix:sn"]},
        ),
        WordEntry(
            word_id="word_snow",
            surface_form="SNOW",
            normalized="snow",
            known_group_hints={"lexical": "starts_with_sn"},
            metadata={"lexical_signals": ["prefix:sn"]},
        ),
        WordEntry(
            word_id="word_snug",
            surface_form="SNUG",
            normalized="snug",
            known_group_hints={"lexical": "starts_with_sn"},
            metadata={"lexical_signals": ["prefix:sn"]},
        ),
        WordEntry(
            word_id="word_bash",
            surface_form="BASH",
            normalized="bash",
            known_group_hints={"lexical": "ends_with_ash"},
            metadata={"lexical_signals": ["suffix:ash"]},
        ),
        WordEntry(
            word_id="word_cash",
            surface_form="CASH",
            normalized="cash",
            known_group_hints={"lexical": "ends_with_ash"},
            metadata={"lexical_signals": ["suffix:ash"]},
        ),
        WordEntry(
            word_id="word_dash",
            surface_form="DASH",
            normalized="dash",
            known_group_hints={"lexical": "ends_with_ash"},
            metadata={"lexical_signals": ["suffix:ash"]},
        ),
        WordEntry(
            word_id="word_mash",
            surface_form="MASH",
            normalized="mash",
            known_group_hints={"lexical": "ends_with_ash"},
            metadata={"lexical_signals": ["suffix:ash"]},
        ),
        WordEntry(
            word_id="word_blinky",
            surface_form="BLINKY",
            normalized="blinky",
            known_group_hints={"theme": "pacman_ghosts"},
            metadata={"theme_tags": ["pacman", "ghost"]},
        ),
        WordEntry(
            word_id="word_inky",
            surface_form="INKY",
            normalized="inky",
            known_group_hints={"theme": "pacman_ghosts"},
            metadata={"theme_tags": ["pacman", "ghost"]},
        ),
        WordEntry(
            word_id="word_pinky",
            surface_form="PINKY",
            normalized="pinky",
            known_group_hints={"theme": "pacman_ghosts"},
            metadata={"theme_tags": ["pacman", "ghost"]},
        ),
        WordEntry(
            word_id="word_clyde",
            surface_form="CLYDE",
            normalized="clyde",
            known_group_hints={"theme": "pacman_ghosts"},
            metadata={"theme_tags": ["pacman", "ghost"]},
        ),
        WordEntry(
            word_id="word_leonardo",
            surface_form="LEONARDO",
            normalized="leonardo",
            known_group_hints={"theme": "tmnt"},
            metadata={"theme_tags": ["tmnt", "fictional_character"]},
        ),
        WordEntry(
            word_id="word_donatello",
            surface_form="DONATELLO",
            normalized="donatello",
            known_group_hints={"theme": "tmnt"},
            metadata={"theme_tags": ["tmnt", "fictional_character"]},
        ),
        WordEntry(
            word_id="word_raphael",
            surface_form="RAPHAEL",
            normalized="raphael",
            known_group_hints={"theme": "tmnt"},
            metadata={"theme_tags": ["tmnt", "fictional_character"]},
        ),
        WordEntry(
            word_id="word_michelangelo",
            surface_form="MICHELANGELO",
            normalized="michelangelo",
            known_group_hints={"theme": "tmnt"},
            metadata={"theme_tags": ["tmnt", "fictional_character"]},
        ),
    ]


def _context() -> GenerationContext:
    return GenerationContext(
        request_id="req_stage2",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=[GroupType.SEMANTIC, GroupType.LEXICAL, GroupType.THEME],
    )


def _composer_group(
    *,
    group_type: GroupType,
    label: str,
    prefix: str,
    confidence: float,
    centroid: list[float],
    shared_signals: list[str],
) -> GroupCandidate:
    words = [f"{prefix.upper()}{index}" for index in range(1, 5)]
    word_ids = [f"{prefix.lower()}_{index}" for index in range(1, 5)]
    metadata = {
        "normalized_label": label.lower().replace(" ", "_"),
        "shared_tags": shared_signals,
        "semantic_centroid": centroid,
        "mean_pairwise_similarity": 0.9,
        "evidence": {"shared_signals": shared_signals},
    }
    if group_type is GroupType.LEXICAL:
        metadata.update(
            {
                "pattern_type": "shared_prefix",
                "normalized_pattern": prefix.lower(),
                "rule_signature": f"lexical:shared_prefix:{prefix.lower()}",
            }
        )
    if group_type is GroupType.THEME:
        metadata.update(
            {
                "theme_name": label.lower().replace(" ", "_"),
                "theme_source": "curated_theme_inventory_v1",
                "rule_signature": f"theme:{label.lower().replace(' ', '_')}",
            }
        )
    return GroupCandidate(
        candidate_id=f"{group_type.value}_{prefix.lower()}",
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


def _weak_lexical_group(
    entries: list[WordEntry],
    features_by_word_id,
) -> GroupCandidate:
    entries_by_id = {entry.word_id: entry for entry in entries}
    word_ids = ["word_snap", "word_snip", "word_bash", "word_cash"]
    vectors = [
        features_by_word_id[word_id].debug_attributes["semantic_sketch"] for word_id in word_ids
    ]
    return GroupCandidate(
        candidate_id="lexical_fake_sn",
        group_type=GroupType.LEXICAL,
        label="Starts with SN",
        rationale="Deliberately weak lexical grouping for Stage 1 regression coverage.",
        words=[entries_by_id[word_id].surface_form for word_id in word_ids],
        word_ids=word_ids,
        source_strategy="test",
        extraction_mode="semantic_baseline_v1",
        confidence=0.62,
        metadata={
            "normalized_label": "starts_with_sn",
            "pattern_type": "shared_prefix",
            "normalized_pattern": "sn",
            "rule_signature": "lexical:shared_prefix:sn",
            "shared_tags": ["prefix_sn"],
            "semantic_centroid": [round(value, 6) for value in vector_centroid(vectors)],
            "mean_pairwise_similarity": round(mean_pairwise_similarity(vectors), 4),
            "evidence": {"shared_signals": ["prefix_sn"]},
        },
    )


def test_human_lexical_generator_emits_real_traceable_candidates() -> None:
    entries = _stage2_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }
    generator = HumanLexicalGroupGenerator()

    first = generator.generate(entries, features_by_word_id, _context())
    second = generator.generate(entries, features_by_word_id, _context())

    assert first
    assert all(candidate.group_type is GroupType.LEXICAL for candidate in first)
    assert [candidate.candidate_id for candidate in first] == [
        candidate.candidate_id for candidate in second
    ]

    starts_with_sn = next(candidate for candidate in first if candidate.label == "Starts with SN")
    assert starts_with_sn.words == ["SNAP", "SNIP", "SNOW", "SNUG"]
    assert starts_with_sn.metadata["pattern_type"] == "shared_prefix"
    assert starts_with_sn.metadata["normalized_pattern"] == "sn"
    assert starts_with_sn.metadata["rule_signature"] == "lexical:shared_prefix:sn"
    assert starts_with_sn.metadata["evidence"]["matched_feature"] == "prefix:sn"
    assert len(starts_with_sn.metadata["evidence"]["word_matches"]) == 4
    assert starts_with_sn.metadata["provenance"]["generator"] == "human_lexical_group_generator"


def test_human_lexical_generator_filters_duplicate_or_weak_pattern_views() -> None:
    entries = _stage2_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }

    candidates = HumanLexicalGroupGenerator().generate(entries, features_by_word_id, _context())

    ash_groups = [
        candidate
        for candidate in candidates
        if set(candidate.words) == {"BASH", "CASH", "DASH", "MASH"}
    ]
    assert len(ash_groups) == 1
    assert ash_groups[0].metadata["pattern_type"] == "shared_suffix"
    assert ash_groups[0].metadata["normalized_pattern"] == "ash"
    assert all(
        not candidate.metadata["rule_signature"].startswith("lexical:length")
        for candidate in candidates
    )
    assert all(
        not candidate.metadata["rule_signature"].startswith("lexical:shape")
        for candidate in candidates
    )


def test_human_theme_generator_emits_curated_candidates_with_provenance() -> None:
    entries = _stage2_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }
    generator = HumanThemeGroupGenerator()

    first = generator.generate(entries, features_by_word_id, _context())
    second = generator.generate(entries, features_by_word_id, _context())

    assert first
    assert all(candidate.group_type is GroupType.THEME for candidate in first)
    assert [candidate.candidate_id for candidate in first] == [
        candidate.candidate_id for candidate in second
    ]

    ghosts = next(candidate for candidate in first if candidate.label == "Pac-Man ghosts")
    assert ghosts.words == ["BLINKY", "CLYDE", "INKY", "PINKY"]
    assert ghosts.metadata["theme_name"] == "pac_man_ghosts"
    assert ghosts.metadata["theme_source"] == "curated_theme_inventory_v1"
    assert ghosts.metadata["rule_signature"] == "theme:pac_man_ghosts"
    assert ghosts.metadata["provenance"]["generator"] == "human_theme_group_generator"
    assert len(ghosts.metadata["evidence"]["membership"]) == 4
    assert ghosts.metadata["evidence"]["membership"][0]["source"] == "curated_theme_inventory_v1"


def test_human_theme_generator_filters_duplicate_or_generic_theme_labels() -> None:
    entries = _stage2_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }

    candidates = HumanThemeGroupGenerator().generate(entries, features_by_word_id, _context())

    ghosts = [
        candidate
        for candidate in candidates
        if set(candidate.words) == {"BLINKY", "INKY", "PINKY", "CLYDE"}
    ]
    turtles = [
        candidate
        for candidate in candidates
        if set(candidate.words) == {"LEONARDO", "DONATELLO", "RAPHAEL", "MICHELANGELO"}
    ]
    assert len(ghosts) == 1
    assert len(turtles) == 1
    assert all(candidate.label.lower() != "things" for candidate in candidates)


def test_human_puzzle_composer_prefers_semantic_majority_shape_over_theme_formula() -> None:
    composer = HumanPuzzleComposer()
    context = _context()
    groups = {
        GroupType.SEMANTIC.value: [
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Planets",
                prefix="sem_a",
                confidence=0.87,
                centroid=[1.0, 0.0, 0.0, 0.0],
                shared_signals=["planet"],
            ),
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Gemstones",
                prefix="sem_b",
                confidence=0.87,
                centroid=[0.0, 1.0, 0.0, 0.0],
                shared_signals=["gemstone"],
            ),
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Birds",
                prefix="sem_c",
                confidence=0.87,
                centroid=[0.64, 0.64, 0.0, 0.0],
                shared_signals=["bird"],
            ),
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Aircraft",
                prefix="sem_d",
                confidence=0.87,
                centroid=[0.6, 0.6, 0.0, 0.0],
                shared_signals=["aircraft"],
            ),
        ],
        GroupType.LEXICAL.value: [
            _composer_group(
                group_type=GroupType.LEXICAL,
                label="Starts with SN",
                prefix="lex_a",
                confidence=0.84,
                centroid=[0.0, 0.0, 1.0, 0.0],
                shared_signals=["prefix_sn"],
            )
        ],
        GroupType.THEME.value: [
            _composer_group(
                group_type=GroupType.THEME,
                label="Pac-Man ghosts",
                prefix="theme_a",
                confidence=0.84,
                centroid=[0.0, 0.0, 0.0, 1.0],
                shared_signals=["pacman", "ghost"],
            )
        ],
    }

    puzzles = composer.compose(groups, context)

    assert puzzles
    selected = puzzles[0]
    assert selected.metadata["semantic_group_count"] >= 3
    assert "theme" not in selected.metadata["mechanism_mix_summary"]
    assert set(group.group_type for group in selected.groups).issubset(
        {GroupType.SEMANTIC, GroupType.LEXICAL}
    )
    assert selected.metadata["composition_trace"]["selection_summary"]["diversity_bonus"] > 0.0


def test_human_puzzle_composer_keeps_semantic_only_fallback_when_mixed_board_is_weaker() -> None:
    composer = HumanPuzzleComposer()
    context = _context()
    groups = {
        GroupType.SEMANTIC.value: [
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Planets",
                prefix="sem_a",
                confidence=0.87,
                centroid=[1.0, 0.0, 0.0, 0.0],
                shared_signals=["planet"],
            ),
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Gemstones",
                prefix="sem_b",
                confidence=0.87,
                centroid=[0.0, 1.0, 0.0, 0.0],
                shared_signals=["gemstone"],
            ),
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Birds",
                prefix="sem_c",
                confidence=0.87,
                centroid=[0.0, 0.0, 1.0, 0.0],
                shared_signals=["bird"],
            ),
            _composer_group(
                group_type=GroupType.SEMANTIC,
                label="Fish",
                prefix="sem_d",
                confidence=0.87,
                centroid=[0.0, 0.0, 0.0, 1.0],
                shared_signals=["fish"],
            ),
        ],
        GroupType.LEXICAL.value: [
            _composer_group(
                group_type=GroupType.LEXICAL,
                label="Starts with SN",
                prefix="lex_a",
                confidence=0.7,
                centroid=[0.4, 0.4, 0.4, 0.0],
                shared_signals=["prefix_sn"],
            )
        ],
        GroupType.THEME.value: [
            _composer_group(
                group_type=GroupType.THEME,
                label="Pac-Man ghosts",
                prefix="theme_a",
                confidence=0.7,
                centroid=[0.4, 0.4, 0.0, 0.4],
                shared_signals=["pacman", "ghost"],
            )
        ],
    }

    puzzles = composer.compose(groups, context)

    assert puzzles
    selected = puzzles[0]
    assert [group.group_type for group in selected.groups] == [GroupType.SEMANTIC] * 4
    assert selected.metadata["mixed_board"] is False
    assert selected.metadata["mechanism_mix_summary"] == {"semantic": 4}


def test_stage1_quality_control_separates_stronger_mixed_from_weaker_formula() -> None:
    entries = _stage2_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }
    context = _context()
    context.run_metadata["features_by_word_id"] = features_by_word_id

    semantic_candidates = HumanSemanticGroupGenerator().generate(
        entries, features_by_word_id, context
    )
    lexical_candidates = HumanLexicalGroupGenerator().generate(
        entries, features_by_word_id, context
    )
    theme_candidates = HumanThemeGroupGenerator().generate(entries, features_by_word_id, context)

    strong_groups = [
        next(candidate for candidate in semantic_candidates if candidate.label == "Planets"),
        next(candidate for candidate in semantic_candidates if candidate.label == "Pacman Ghosts"),
        next(candidate for candidate in semantic_candidates if candidate.label == "TMNT"),
        next(candidate for candidate in lexical_candidates if candidate.label == "Ends with -ASH"),
    ]
    strong_puzzle = PuzzleCandidate(
        puzzle_id="strong_mixed_stage2",
        board_words=[word for group in strong_groups for word in group.words],
        groups=strong_groups,
    )

    weak_groups = [
        next(candidate for candidate in semantic_candidates if candidate.label == "Planets"),
        _weak_lexical_group(entries, features_by_word_id),
        next(candidate for candidate in theme_candidates if candidate.label == "Pac-Man ghosts"),
        next(
            candidate
            for candidate in theme_candidates
            if candidate.label == "Teenage Mutant Ninja Turtles"
        ),
    ]
    weak_puzzle = PuzzleCandidate(
        puzzle_id="weak_mixed_stage2",
        board_words=[word for group in weak_groups for word in group.words],
        groups=weak_groups,
    )

    verifier = InternalPuzzleVerifier(solver=MockSolverBackend())
    scorer = HumanOwnedPuzzleScorer()

    strong_verification = verifier.verify(strong_puzzle, context)
    weak_verification = verifier.verify(weak_puzzle, context)
    strong_score = scorer.score(strong_puzzle, strong_verification, context)
    weak_score = scorer.score(weak_puzzle, weak_verification, context)

    assert strong_verification.passed is True
    assert strong_verification.decision == "accept"
    assert strong_score.overall > 0.2

    assert weak_verification.decision in {"borderline", "reject"}
    assert (
        weak_verification.summary_metrics["weakest_group_support"]
        < strong_verification.summary_metrics["weakest_group_support"]
    )
    assert weak_score.overall < strong_score.overall
