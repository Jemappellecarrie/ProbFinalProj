"""Tests for the semantic baseline hand-port."""

from __future__ import annotations

from app.core.enums import GenerationMode, GroupType
from app.domain.value_objects import GenerationContext
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.generators.semantic import HumanSemanticGroupGenerator
from app.pipeline.builder import HumanPuzzleComposer
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate, SolverResult
from app.solver.human_ambiguity_strategy import ExperimentalSemanticAmbiguityEvaluator


def _semantic_seed_entries() -> list[WordEntry]:
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
            word_id="word_ruby",
            surface_form="RUBY",
            normalized="ruby",
            known_group_hints={"semantic": "gemstones"},
            metadata={"semantic_tags": ["gemstone", "mineral"]},
        ),
        WordEntry(
            word_id="word_opal",
            surface_form="OPAL",
            normalized="opal",
            known_group_hints={"semantic": "gemstones"},
            metadata={"semantic_tags": ["gemstone", "mineral"]},
        ),
        WordEntry(
            word_id="word_jade",
            surface_form="JADE",
            normalized="jade",
            known_group_hints={"semantic": "gemstones"},
            metadata={"semantic_tags": ["gemstone", "mineral"]},
        ),
        WordEntry(
            word_id="word_topaz",
            surface_form="TOPAZ",
            normalized="topaz",
            known_group_hints={"semantic": "gemstones"},
            metadata={"semantic_tags": ["gemstone", "mineral"]},
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


def _semantic_context() -> GenerationContext:
    return GenerationContext(
        request_id="req_semantic",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=17,
        requested_group_types=[GroupType.SEMANTIC],
    )


def _group(words: list[str], word_ids: list[str], label: str, confidence: float) -> GroupCandidate:
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
        metadata={},
    )


def _feature(word_id: str, normalized: str, sketch: list[float]) -> WordFeatures:
    return WordFeatures(
        word_id=word_id,
        normalized=normalized,
        semantic_tags=[],
        lexical_signals=[],
        phonetic_signals=[],
        theme_tags=[],
        extraction_mode="semantic_baseline_v1",
        provenance=["test"],
        debug_attributes={"semantic_sketch": sketch},
    )


def test_human_feature_extractor_builds_deterministic_semantic_sketches() -> None:
    extractor = HumanCuratedFeatureExtractor()

    features = extractor.extract_features(_semantic_seed_entries())
    repeated = extractor.extract_features(_semantic_seed_entries())
    features_by_id = {feature.word_id: feature for feature in features}
    repeated_by_id = {feature.word_id: feature for feature in repeated}

    mercury = features_by_id["word_mercury"]
    blinky = features_by_id["word_blinky"]

    assert mercury.extraction_mode == "semantic_baseline_v1"
    assert "planet" in mercury.semantic_tags
    assert "pacman" in blinky.theme_tags
    assert "semantic_sketch" in mercury.debug_attributes
    assert len(mercury.debug_attributes["semantic_sketch"]) == 32
    assert (
        mercury.debug_attributes["semantic_sketch"]
        == repeated_by_id["word_mercury"].debug_attributes["semantic_sketch"]
    )
    assert "planet" in mercury.debug_attributes["semantic_evidence"]["semantic_tokens"]


def test_human_feature_extractor_canonicalizes_and_surfaces_collision_metadata() -> None:
    extractor = HumanCuratedFeatureExtractor()
    entries = [
        WordEntry(
            word_id="word_space_1",
            surface_form="  Space-Bar  ",
            normalized=" Space Bar ",
            known_group_hints={"semantic": "Sky Objects"},
            metadata={"semantic_tags": ["  Astronomy ", " Planet! "]},
        ),
        WordEntry(
            word_id="word_space_2",
            surface_form="SPACE BAR",
            normalized="space_bar",
            known_group_hints={"semantic": "sky_objects"},
            metadata={"semantic_tags": ["astronomy", "planet"]},
        ),
        WordEntry(
            word_id="word_sparse",
            surface_form="LONE",
            normalized="Lone",
            metadata={},
        ),
    ]

    features = extractor.extract_features(entries)
    features_by_id = {feature.word_id: feature for feature in features}

    canonical = features_by_id["word_space_1"]
    collision = features_by_id["word_space_2"]
    sparse = features_by_id["word_sparse"]

    assert canonical.normalized == "space_bar"
    assert canonical.semantic_tags == ["astronomy", "planet", "sky_objects"]
    assert canonical.debug_attributes["canonical_form"]["display_form"] == "Space-Bar"
    assert canonical.debug_attributes["canonical_form"]["canonical_normalized"] == "space_bar"
    assert canonical.debug_attributes["canonical_form"]["collision_count"] == 2
    assert collision.debug_attributes["canonical_form"]["colliding_word_ids"] == [
        "word_space_1",
        "word_space_2",
    ]
    assert canonical.debug_attributes["raw_source_facts"]["semantic_metadata"] == [
        "Astronomy",
        "Planet!",
    ]
    assert sparse.debug_attributes["support"]["support_level"] == "surface_only"
    assert sparse.debug_attributes["semantic_evidence"]["semantic_tokens"] == []


def test_human_semantic_generator_returns_four_word_candidates_with_evidence() -> None:
    entries = _semantic_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features = extractor.extract_features(entries)
    features_by_word_id = {feature.word_id: feature for feature in features}

    generator = HumanSemanticGroupGenerator()
    candidates = generator.generate(entries, features_by_word_id, _semantic_context())

    assert candidates
    assert all(candidate.group_type is GroupType.SEMANTIC for candidate in candidates)

    planets = next(
        candidate
        for candidate in candidates
        if set(candidate.words) == {"MERCURY", "VENUS", "EARTH", "MARS"}
    )
    assert planets.confidence > 0.0
    assert planets.metadata["shared_tags"]
    assert "semantic_centroid" in planets.metadata


def test_human_semantic_generator_emits_stable_traceable_candidates() -> None:
    entries = _semantic_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features_by_word_id = {
        feature.word_id: feature for feature in extractor.extract_features(entries)
    }
    generator = HumanSemanticGroupGenerator()

    first = generator.generate(entries, features_by_word_id, _semantic_context())
    second = generator.generate(entries, features_by_word_id, _semantic_context())

    assert [candidate.candidate_id for candidate in first] == [
        candidate.candidate_id for candidate in second
    ]

    planets = next(candidate for candidate in first if candidate.label == "Planets")
    assert planets.metadata["normalized_label"] == "planets"
    assert planets.metadata["rule_signature"] == "semantic:astronomy"
    assert planets.metadata["provenance"]["generator"] == "human_semantic_group_generator"
    assert planets.metadata["evidence"]["shared_signals"] == [
        "astronomy",
        "planet",
        "planets",
    ]
    assert len(planets.metadata["evidence"]["member_scores"]) == 4
    assert planets.metadata["diagnostics"]["duplicate_signals_merged"] == ["planet", "planets"]


def test_human_puzzle_composer_builds_valid_semantic_puzzle() -> None:
    entries = _semantic_seed_entries()
    extractor = HumanCuratedFeatureExtractor()
    features = extractor.extract_features(entries)
    features_by_word_id = {feature.word_id: feature for feature in features}
    generator = HumanSemanticGroupGenerator()
    candidates = generator.generate(entries, features_by_word_id, _semantic_context())

    composer = HumanPuzzleComposer()
    puzzles = composer.compose({GroupType.SEMANTIC.value: candidates}, _semantic_context())

    assert puzzles
    puzzle = puzzles[0]
    assert len(puzzle.groups) == 4
    assert len(puzzle.board_words) == 16
    assert len(set(puzzle.board_words)) == 16
    assert all(group.group_type is GroupType.SEMANTIC for group in puzzle.groups)
    assert puzzle.metadata["semantic_group_count"] == 4


def test_human_puzzle_composer_reports_structured_failure_reasons() -> None:
    context = _semantic_context()
    composer = HumanPuzzleComposer()
    groups = {
        GroupType.SEMANTIC.value: [
            _group(["ALPHA", "BETA", "GAMMA", "DELTA"], ["a1", "a2", "a3", "a4"], "A", 0.9),
            _group(["ALPHA", "EPSILON", "ZETA", "ETA"], ["a1", "b1", "b2", "b3"], "B", 0.88),
            _group(["THETA", "IOTA", "KAPPA", "LAMBDA"], ["c1", "c2", "c3", "c4"], "C", 0.87),
            _group(["MU", "NU", "XI", "OMICRON"], ["d1", "d2", "d3", "d4"], "D", 0.86),
        ]
    }

    puzzles = composer.compose(groups, context)

    assert puzzles == []
    diagnostics = context.run_metadata["composition_diagnostics"]
    assert diagnostics["failure_reasons"] == ["insufficient_non_overlapping_groups"]
    assert diagnostics["rejected_combinations"][0]["reason"] == "overlapping_words"
    assert diagnostics["rejected_combinations"][0]["overlapping_word_ids"] == ["a1"]


def test_experimental_semantic_ambiguity_evaluator_flags_high_leakage() -> None:
    groups = [
        _group(["ALPHA", "BETA", "GAMMA", "DELTA"], ["a1", "a2", "a3", "a4"], "Group A", 0.8),
        _group(["EPSILON", "ZETA", "ETA", "THETA"], ["b1", "b2", "b3", "b4"], "Group B", 0.8),
        _group(["IOTA", "KAPPA", "LAMBDA", "MU"], ["c1", "c2", "c3", "c4"], "Group C", 0.8),
        _group(["NU", "XI", "OMICRON", "PI"], ["d1", "d2", "d3", "d4"], "Group D", 0.8),
    ]
    puzzle = PuzzleCandidate(
        puzzle_id="puzzle_semantic",
        board_words=[word for group in groups for word in group.words],
        groups=groups,
        compatibility_notes=[],
        metadata={},
    )
    features_by_word_id = {
        "a1": _feature("a1", "alpha", [1.0, 0.0, 0.0, 0.0]),
        "a2": _feature("a2", "beta", [1.0, 0.0, 0.0, 0.0]),
        "a3": _feature("a3", "gamma", [1.0, 0.0, 0.0, 0.0]),
        "a4": _feature("a4", "delta", [1.0, 0.0, 0.0, 0.0]),
        "b1": _feature("b1", "epsilon", [0.95, 0.05, 0.0, 0.0]),
        "b2": _feature("b2", "zeta", [0.95, 0.05, 0.0, 0.0]),
        "b3": _feature("b3", "eta", [0.95, 0.05, 0.0, 0.0]),
        "b4": _feature("b4", "theta", [0.95, 0.05, 0.0, 0.0]),
        "c1": _feature("c1", "iota", [0.0, 1.0, 0.0, 0.0]),
        "c2": _feature("c2", "kappa", [0.0, 1.0, 0.0, 0.0]),
        "c3": _feature("c3", "lambda", [0.0, 1.0, 0.0, 0.0]),
        "c4": _feature("c4", "mu", [0.0, 1.0, 0.0, 0.0]),
        "d1": _feature("d1", "nu", [0.0, 0.0, 1.0, 0.0]),
        "d2": _feature("d2", "xi", [0.0, 0.0, 1.0, 0.0]),
        "d3": _feature("d3", "omicron", [0.0, 0.0, 1.0, 0.0]),
        "d4": _feature("d4", "pi", [0.0, 0.0, 1.0, 0.0]),
    }
    context = GenerationContext(
        request_id="req_ambiguity",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        run_metadata={"features_by_word_id": features_by_word_id},
    )
    solver_result = SolverResult(
        backend_name="mock_solver_backend",
        solved=True,
        confidence=1.0,
        proposed_groups=[group.words for group in groups],
        alternative_groupings_detected=2,
        notes=[],
        raw_output={},
    )

    verification = ExperimentalSemanticAmbiguityEvaluator().evaluate(
        puzzle,
        solver_result,
        context,
    )

    assert verification.ambiguity_report is not None
    assert verification.ambiguity_report.reject_recommended is True
    assert verification.ambiguity_score > 0.4
    assert (
        "cross_group_semantic_similarity" in verification.ambiguity_report.evidence.triggered_flags
    )
