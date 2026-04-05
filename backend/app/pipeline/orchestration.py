"""End-to-end pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.editorial_quality import (
    ensure_run_family_accounting,
    recent_winner_history_count,
    record_recent_winner_signature,
    record_run_family_event,
    record_run_winner_suppression,
    run_family_count,
)
from app.core.stage1_quality import verification_decision_rank
from app.domain.protocols import (
    PuzzleComposer,
    PuzzleScorer,
    PuzzleVerifier,
    WordFeatureExtractor,
    WordRepository,
)
from app.domain.value_objects import ComponentSelection, GenerationContext
from app.generators.base import BaseGroupGenerator
from app.pipeline.trace import TraceRecorder
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.schemas.trace_models import GenerationTrace


@dataclass(slots=True)
class PipelineRunResult:
    """Aggregate result returned by the orchestration layer."""

    puzzle: PuzzleCandidate
    verification: VerificationResult
    score: PuzzleScore
    trace: GenerationTrace | None
    warnings: list[str]
    components: ComponentSelection
    candidate_results: list[CandidateEvaluationResult] = field(default_factory=list)
    generator_diagnostics: dict[str, Any] = field(default_factory=dict)
    composition_diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateEvaluationResult:
    """One ranked candidate board evaluated during a pipeline run."""

    request_rank: int
    selected: bool
    puzzle: PuzzleCandidate
    verification: VerificationResult
    score: PuzzleScore


class PuzzleGenerationPipeline:
    """Coordinate repositories, feature extraction, generation, verification, and scoring."""

    def __init__(
        self,
        word_repository: WordRepository,
        feature_extractor: WordFeatureExtractor,
        generators: list[BaseGroupGenerator],
        composer: PuzzleComposer,
        verifier: PuzzleVerifier,
        scorer: PuzzleScorer,
        components: ComponentSelection,
    ) -> None:
        self._word_repository = word_repository
        self._feature_extractor = feature_extractor
        self._generators = generators
        self._composer = composer
        self._verifier = verifier
        self._scorer = scorer
        self._components = components

    @staticmethod
    def _selection_decision_rank(
        verification: VerificationResult,
        *,
        style_metrics: dict[str, float],
        score: PuzzleScore,
    ) -> int:
        """Return a request-level selection rank that can soften fragile accepts."""

        decision = verification.decision.value
        if decision != "accept":
            return verification_decision_rank(decision)

        weakest_group_support = float(score.components.get("weakest_group_support", 0.0))
        style_alignment_score = float(style_metrics.get("style_alignment_score", 0.0))
        semantic_group_count = float(style_metrics.get("semantic_group_count", 0.0))
        theme_group_count = float(style_metrics.get("theme_group_count", 0.0))
        editorial_payoff_score = float(style_metrics.get("editorial_payoff_score", 0.0))
        surface_wordplay_group_count = float(style_metrics.get("surface_wordplay_group_count", 0.0))

        if weakest_group_support < 0.8:
            return verification_decision_rank("borderline")
        if style_alignment_score < 0.75:
            return verification_decision_rank("borderline")
        if semantic_group_count < 3.0 and theme_group_count >= 1.0 and editorial_payoff_score < 0.82:
            return verification_decision_rank("borderline")
        if semantic_group_count <= 1.0 and theme_group_count >= 1.0 and surface_wordplay_group_count >= 1.5:
            return verification_decision_rank("borderline")
        return verification_decision_rank(decision)

    @staticmethod
    def _selection_key(
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        score: PuzzleScore,
        *,
        context: GenerationContext,
        demo_mode: bool,
    ) -> tuple[float, ...] | tuple[int, float, float, str]:
        if demo_mode:
            return (
                -int(verification.passed),
                -score.overall,
                verification.ambiguity_score,
                puzzle.puzzle_id,
            )

        style_metrics = (
            verification.style_analysis.board_style_summary.metrics
            if verification.style_analysis is not None
            and verification.style_analysis.board_style_summary is not None
            else {}
        )
        selection_decision_rank = PuzzleGenerationPipeline._selection_decision_rank(
            verification,
            style_metrics=style_metrics,
            score=score,
        )
        run_state = ensure_run_family_accounting(context.run_metadata.get("editorial_run_state"))
        board_family_signature = str(puzzle.metadata.get("board_family_signature", ""))
        label_family_signature = str(puzzle.metadata.get("label_family_signature", ""))
        editorial_family_signature = str(puzzle.metadata.get("editorial_family_signature", ""))
        template_signature = str(puzzle.metadata.get("mechanism_template_signature", ""))
        theme_family_signatures = list(puzzle.metadata.get("theme_family_signatures", []))
        surface_family_signatures = list(
            puzzle.metadata.get("surface_wordplay_family_signatures", [])
        )
        recent_board_repeat_count = recent_winner_history_count(
            run_state,
            bucket="board",
            signature=board_family_signature,
        )
        recent_editorial_family_repeat_count = recent_winner_history_count(
            run_state,
            bucket="editorial",
            signature=editorial_family_signature,
        )
        recent_label_family_repeat_count = recent_winner_history_count(
            run_state,
            bucket="label",
            signature=label_family_signature,
        )
        recent_template_repeat_count = recent_winner_history_count(
            run_state,
            bucket="template",
            signature=template_signature,
        )
        recent_microtheme_repeat_count = max(
            (
                recent_winner_history_count(
                    run_state,
                    bucket="theme",
                    signature=str(signature),
                )
                for signature in theme_family_signatures
            ),
            default=0,
        )
        recent_surface_repeat_count = max(
            (
                recent_winner_history_count(
                    run_state,
                    bucket="surface",
                    signature=str(signature),
                )
                for signature in surface_family_signatures
            ),
            default=0,
        )
        winner_editorial_family_repeat_count = run_family_count(
            run_state,
            parent_key="winner_family_count_by_run",
            bucket="editorial",
            signature=editorial_family_signature,
        )
        winner_label_family_repeat_count = run_family_count(
            run_state,
            parent_key="winner_family_count_by_run",
            bucket="label",
            signature=label_family_signature,
        )
        winner_template_repeat_count = run_family_count(
            run_state,
            parent_key="winner_family_count_by_run",
            bucket="template",
            signature=template_signature,
        )
        winner_microtheme_repeat_count = max(
            (
                run_family_count(
                    run_state,
                    parent_key="winner_family_count_by_run",
                    bucket="theme",
                    signature=str(signature),
                )
                for signature in theme_family_signatures
            ),
            default=0,
        )
        winner_surface_repeat_count = max(
            (
                run_family_count(
                    run_state,
                    parent_key="winner_family_count_by_run",
                    bucket="surface",
                    signature=str(signature),
                )
                for signature in surface_family_signatures
            ),
            default=0,
        )
        semantic_majority_preference = 1 if puzzle.metadata.get("semantic_majority_board") else 0
        weakest_group_support = float(score.components.get("weakest_group_support", 0.0))
        style_alignment_score = float(style_metrics.get("style_alignment_score", 0.0))
        semantic_group_count = float(style_metrics.get("semantic_group_count", 0.0))
        wordplay_group_count = float(style_metrics.get("wordplay_group_count", 0.0))
        theme_group_count = float(style_metrics.get("theme_group_count", 0.0))
        surface_wordplay_score = float(style_metrics.get("surface_wordplay_score", 0.0))
        surface_wordplay_penalty_applied = float(
            style_metrics.get("surface_wordplay_penalty_applied", 0.0)
        )
        microtheme_smallness = float(style_metrics.get("microtheme_smallness", 0.0))
        clue_payoff_bonus_applied = float(style_metrics.get("clue_payoff_bonus_applied", 0.0))
        label_naturalness_score = float(style_metrics.get("label_naturalness_score", 0.0))
        low_payoff_pattern_flags = float(style_metrics.get("low_payoff_pattern_flags", 0.0))
        label_family_fragility_signals = sum(
            (
                style_alignment_score < 0.88,
                weakest_group_support < 0.82,
                score.overall < 0.975,
                semantic_group_count < 3.0,
                surface_wordplay_score >= 0.45,
                float(style_metrics.get("formulaic_mix_score", 0.0)) >= 0.28,
            )
        )
        repeated_label_family_fragile_accept = int(
            selection_decision_rank == verification_decision_rank("accept")
            and recent_label_family_repeat_count >= 3
            and label_family_fragility_signals >= 2
        )
        if repeated_label_family_fragile_accept:
            selection_decision_rank = verification_decision_rank("borderline")
        one_semantic_plus_microtheme_surface = int(
            semantic_group_count <= 1
            and theme_group_count >= 1
            and surface_wordplay_score >= 0.6
        )
        balanced_mixed_surface_stack = int(
            bool(puzzle.metadata.get("balanced_mixed_board"))
            and theme_group_count >= 1
            and wordplay_group_count >= 1
        )
        low_semantic_surface_stack = int(
            semantic_group_count <= 1
            and wordplay_group_count >= 1
            and (
                theme_group_count >= 1
                or surface_wordplay_score >= 0.6
                or microtheme_smallness >= 0.65
            )
        )
        return (
            -selection_decision_rank,
            recent_board_repeat_count,
            repeated_label_family_fragile_accept,
            recent_label_family_repeat_count,
            recent_editorial_family_repeat_count,
            recent_template_repeat_count,
            recent_microtheme_repeat_count,
            recent_surface_repeat_count,
            winner_label_family_repeat_count,
            winner_editorial_family_repeat_count,
            winner_template_repeat_count,
            winner_microtheme_repeat_count,
            winner_surface_repeat_count,
            one_semantic_plus_microtheme_surface,
            balanced_mixed_surface_stack,
            low_semantic_surface_stack,
            -semantic_majority_preference,
            -semantic_group_count,
            low_payoff_pattern_flags,
            surface_wordplay_penalty_applied,
            microtheme_smallness,
            verification.ambiguity_score,
            float(style_metrics.get("formulaic_mix_score", 0.0)),
            surface_wordplay_score,
            -clue_payoff_bonus_applied,
            -float(style_metrics.get("phrase_payoff_score", 0.0)),
            -label_naturalness_score,
            -score.overall,
            -float(puzzle.metadata.get("ranking_score", score.overall)),
            puzzle.puzzle_id,
        )

    def run(self, context: GenerationContext) -> PipelineRunResult:
        trace_recorder = TraceRecorder(context.request_id, context.mode, self._components)
        warnings = (
            [
                "Demo mode is active.",
                (
                    "Baseline/mock components are being used for generation, "
                    "verification, and scoring."
                ),
                (
                    "Ambiguity, solver ensemble, and style-analysis outputs are "
                    "scaffold reports only."
                ),
            ]
            if context.demo_mode
            else [
                "Stage 2 mixed-generation mode is active.",
                (
                    "Feature extraction, semantic generation, lexical/theme diversity, "
                    "composition, and Stage 1 quality-control are active."
                ),
                (
                    "Ambiguity analysis, verification, and ranking use the Stage 1 core plus "
                    "Stage 3 phonetic, style-analysis, and calibration-aware bonuses."
                ),
            ]
        )

        entries = self._word_repository.list_entries()
        trace_recorder.add("seed_load", "Loaded seed entries.", {"count": len(entries)})

        features = self._feature_extractor.extract_features(entries)
        features_by_word_id = {feature.word_id: feature for feature in features}
        context.run_metadata["features_by_word_id"] = features_by_word_id
        collision_count = sum(
            1
            for feature in features
            if feature.debug_attributes.get("canonical_form", {}).get("collision_count", 1) > 1
        )
        sparse_support_count = sum(
            1
            for feature in features
            if feature.debug_attributes.get("support", {}).get("support_level") == "surface_only"
        )
        trace_recorder.add(
            "feature_extraction",
            "Extracted feature records.",
            {
                "count": len(features),
                "canonical_collision_count": collision_count,
                "surface_only_support_count": sparse_support_count,
            },
        )

        groups_by_type: dict[str, list] = {}
        for generator in self._generators:
            candidates = generator.generate(entries, features_by_word_id, context)
            groups_by_type[generator.group_type.value] = candidates
            trace_recorder.add(
                "group_generation",
                f"Generated candidates for {generator.group_type.value}.",
                {
                    "group_type": generator.group_type.value,
                    "strategy": generator.strategy_name,
                    "candidate_count": len(candidates),
                    "top_candidates": [
                        {
                            "candidate_id": candidate.candidate_id,
                            "label": candidate.label,
                            "confidence": candidate.confidence,
                        }
                        for candidate in candidates[:3]
                    ],
                },
            )

        puzzles = self._composer.compose(groups_by_type, context)
        composition_diagnostics = context.run_metadata.get("composition_diagnostics", {})
        trace_recorder.add(
            "composition",
            "Composed puzzle candidates.",
            {
                "count": len(puzzles),
                "failure_reasons": composition_diagnostics.get("failure_reasons", []),
                "candidate_pool_size": composition_diagnostics.get("candidate_pool_size"),
            },
        )
        if not puzzles:
            raise RuntimeError(
                "No puzzle candidates were produced. "
                f"Diagnostics: {composition_diagnostics or 'unavailable'}"
            )

        ranked: list[tuple[PuzzleCandidate, VerificationResult, PuzzleScore]] = []
        for puzzle in puzzles:
            verification = self._verifier.verify(puzzle, context)
            score = self._scorer.score(puzzle, verification, context)
            ranked.append((puzzle, verification, score))

        ranked.sort(
            key=lambda item: self._selection_key(
                item[0],
                item[1],
                item[2],
                context=context,
                demo_mode=context.demo_mode,
            ),
        )
        selected_puzzle, selected_verification, selected_score = ranked[0]
        run_state = ensure_run_family_accounting(context.run_metadata.get("editorial_run_state"))
        selected_theme_signatures = list(
            selected_puzzle.metadata.get("theme_family_signatures", [])
        )
        selected_surface_signatures = list(
            selected_puzzle.metadata.get("surface_wordplay_family_signatures", [])
        )
        winner_editorial_family_repeat_count = run_family_count(
            run_state,
            parent_key="winner_family_count_by_run",
            bucket="editorial",
            signature=str(selected_puzzle.metadata.get("editorial_family_signature", "")),
        )
        winner_label_family_repeat_count = run_family_count(
            run_state,
            parent_key="winner_family_count_by_run",
            bucket="label",
            signature=str(selected_puzzle.metadata.get("label_family_signature", "")),
        )
        winner_template_repeat_count = run_family_count(
            run_state,
            parent_key="winner_family_count_by_run",
            bucket="template",
            signature=str(selected_puzzle.metadata.get("mechanism_template_signature", "")),
        )
        winner_microtheme_repeat_count = max(
            (
                run_family_count(
                    run_state,
                    parent_key="winner_family_count_by_run",
                    bucket="theme",
                    signature=str(signature),
                )
                for signature in selected_theme_signatures
            ),
            default=0,
        )
        winner_surface_repeat_count = max(
            (
                run_family_count(
                    run_state,
                    parent_key="winner_family_count_by_run",
                    bucket="surface",
                    signature=str(signature),
                )
                for signature in selected_surface_signatures
            ),
            default=0,
        )
        candidate_results = [
            CandidateEvaluationResult(
                request_rank=index + 1,
                selected=index == 0,
                puzzle=puzzle,
                verification=verification,
                score=score,
            )
            for index, (puzzle, verification, score) in enumerate(ranked)
        ]
        best_mixed_candidate = composition_diagnostics.get("best_mixed_candidate")
        best_semantic_only_candidate = composition_diagnostics.get("best_semantic_only_candidate")
        if selected_puzzle.metadata.get("mixed_board") and best_semantic_only_candidate is not None:
            selection_reason = "mixed_board_outranked_semantic_only"
        elif not selected_puzzle.metadata.get("mixed_board") and best_mixed_candidate is not None:
            selection_reason = "semantic_only_fallback_retained"
        else:
            selection_reason = "single_path_selected"
        if winner_editorial_family_repeat_count == 0 and any(
            run_family_count(
                run_state,
                parent_key="winner_family_count_by_run",
                bucket="editorial",
                signature=str(candidate_puzzle.metadata.get("editorial_family_signature", "")),
            )
            > 0
            for candidate_puzzle, _, _ in ranked[1:]
        ):
            record_run_winner_suppression(
                run_state,
                reason="winner_editorial_family_repeat_avoided",
                signature=str(selected_puzzle.metadata.get("editorial_family_signature", "")),
            )
        for bucket, signature in (
            ("board", str(selected_puzzle.metadata.get("board_family_signature", ""))),
            ("label", str(selected_puzzle.metadata.get("label_family_signature", ""))),
            ("editorial", str(selected_puzzle.metadata.get("editorial_family_signature", ""))),
            ("template", str(selected_puzzle.metadata.get("mechanism_template_signature", ""))),
        ):
            record_run_family_event(
                run_state,
                parent_key="winner_family_count_by_run",
                bucket=bucket,
                signature=signature,
            )
            record_recent_winner_signature(
                run_state,
                bucket=bucket,
                signature=signature,
            )
        for signature in selected_theme_signatures:
            record_run_family_event(
                run_state,
                parent_key="winner_family_count_by_run",
                bucket="theme",
                signature=str(signature),
            )
            record_recent_winner_signature(
                run_state,
                bucket="theme",
                signature=str(signature),
            )
        for signature in selected_surface_signatures:
            record_run_family_event(
                run_state,
                parent_key="winner_family_count_by_run",
                bucket="surface",
                signature=str(signature),
            )
            record_recent_winner_signature(
                run_state,
                bucket="surface",
                signature=str(signature),
            )
        style_metrics = (
            selected_score.style_analysis.board_style_summary.metrics
            if selected_score.style_analysis is not None
            and selected_score.style_analysis.board_style_summary is not None
            else {}
        )
        selected_style_alignment_score = float(style_metrics.get("style_alignment_score", 0.0))
        selected_weakest_group_support = float(
            selected_score.components.get("weakest_group_support", 0.0)
        )
        selected_semantic_group_count = float(style_metrics.get("semantic_group_count", 0.0))
        selected_surface_wordplay_score = float(style_metrics.get("surface_wordplay_score", 0.0))
        selected_formulaic_mix_score = float(style_metrics.get("formulaic_mix_score", 0.0))
        selected_label_family_fragility_signals = sum(
            (
                selected_style_alignment_score < 0.88,
                selected_weakest_group_support < 0.82,
                selected_score.overall < 0.975,
                selected_semantic_group_count < 3.0,
                selected_surface_wordplay_score >= 0.45,
                selected_formulaic_mix_score >= 0.28,
            )
        )
        repeated_label_family_fragile_accept = int(
            selected_verification.decision.value == "accept"
            and recent_winner_history_count(
                run_state,
                bucket="label",
                signature=str(selected_puzzle.metadata.get("label_family_signature", "")),
            )
            >= 3
            and selected_label_family_fragility_signals >= 2
        )
        selection_summary = {
            "selection_policy": [
                "verification_decision",
                "recent_board_repeat_count",
                "repeated_label_family_fragile_accept",
                "recent_winner_label_family_repeat_count",
                "recent_winner_editorial_family_repeat_count",
                "recent_winner_template_repeat_count",
                "recent_winner_microtheme_repeat_count",
                "recent_winner_surface_repeat_count",
                "winner_label_family_repeat_count",
                "winner_editorial_family_repeat_count",
                "winner_template_repeat_count",
                "winner_microtheme_repeat_count",
                "winner_surface_repeat_count",
                "low_semantic_surface_stack",
                "semantic_majority_preference",
                "semantic_group_count",
                "low_payoff_pattern_flags",
                "surface_wordplay_penalty_applied",
                "microtheme_smallness",
                "ambiguity_penalty",
                "formulaic_mix_score",
                "surface_wordplay_score",
                "clue_payoff_bonus_applied",
                "phrase_payoff_score",
                "label_naturalness_score",
                "scorer_overall",
                "composer_ranking_score",
                "puzzle_id",
            ],
            "verification_decision": selected_verification.decision.value,
            "semantic_group_count": selected_puzzle.metadata.get("semantic_group_count", 0),
            "unique_group_type_count": selected_puzzle.metadata.get("unique_group_type_count", 1),
            "mixed_board": bool(selected_puzzle.metadata.get("mixed_board", False)),
            "mechanism_mix_summary": selected_puzzle.metadata.get("mechanism_mix_summary", {}),
            "semantic_majority_preference": int(
                bool(selected_puzzle.metadata.get("semantic_majority_board"))
            ),
            "recent_board_repeat_count": recent_winner_history_count(
                run_state,
                bucket="board",
                signature=str(selected_puzzle.metadata.get("board_family_signature", "")),
            ),
            "repeated_label_family_fragile_accept": repeated_label_family_fragile_accept,
            "recent_winner_label_family_repeat_count": recent_winner_history_count(
                run_state,
                bucket="label",
                signature=str(selected_puzzle.metadata.get("label_family_signature", "")),
            ),
            "recent_winner_editorial_family_repeat_count": recent_winner_history_count(
                run_state,
                bucket="editorial",
                signature=str(selected_puzzle.metadata.get("editorial_family_signature", "")),
            ),
            "recent_winner_template_repeat_count": recent_winner_history_count(
                run_state,
                bucket="template",
                signature=str(selected_puzzle.metadata.get("mechanism_template_signature", "")),
            ),
            "recent_winner_microtheme_repeat_count": max(
                (
                    recent_winner_history_count(
                        run_state,
                        bucket="theme",
                        signature=str(signature),
                    )
                    for signature in selected_theme_signatures
                ),
                default=0,
            ),
            "recent_winner_surface_repeat_count": max(
                (
                    recent_winner_history_count(
                        run_state,
                        bucket="surface",
                        signature=str(signature),
                    )
                    for signature in selected_surface_signatures
                ),
                default=0,
            ),
            "winner_editorial_family_repeat_count": winner_editorial_family_repeat_count,
            "winner_label_family_repeat_count": winner_label_family_repeat_count,
            "winner_template_repeat_count": winner_template_repeat_count,
            "winner_microtheme_repeat_count": winner_microtheme_repeat_count,
            "winner_surface_repeat_count": winner_surface_repeat_count,
            "low_semantic_surface_stack": int(
                float(style_metrics.get("semantic_group_count", 0.0)) <= 1
                and float(style_metrics.get("wordplay_group_count", 0.0)) >= 1
                and (
                    float(style_metrics.get("theme_group_count", 0.0)) >= 1
                    or float(style_metrics.get("surface_wordplay_score", 0.0)) >= 0.6
                    or float(style_metrics.get("microtheme_smallness", 0.0)) >= 0.65
                )
            ),
            "scorer_overall": selected_score.overall,
            "ambiguity_penalty": selected_verification.ambiguity_score,
            "formulaic_mix_score": float(style_metrics.get("formulaic_mix_score", 0.0)),
            "surface_wordplay_score": float(style_metrics.get("surface_wordplay_score", 0.0)),
            "surface_wordplay_penalty_applied": float(
                style_metrics.get("surface_wordplay_penalty_applied", 0.0)
            ),
            "microtheme_smallness": float(style_metrics.get("microtheme_smallness", 0.0)),
            "low_payoff_pattern_flags": float(style_metrics.get("low_payoff_pattern_flags", 0.0)),
            "clue_payoff_bonus_applied": float(
                style_metrics.get("clue_payoff_bonus_applied", 0.0)
            ),
            "phrase_payoff_score": float(style_metrics.get("phrase_payoff_score", 0.0)),
            "label_naturalness_score": float(style_metrics.get("label_naturalness_score", 0.0)),
            "style_alignment_score": selected_style_alignment_score,
            "composer_ranking_score": selected_puzzle.metadata.get("ranking_score", 0.0),
            "selection_reason": selection_reason,
            "puzzle_id": selected_puzzle.puzzle_id,
        }
        selected_puzzle.metadata.setdefault("composition_trace", {})
        selected_puzzle.metadata["composition_trace"]["selection_policy"] = selection_summary[
            "selection_policy"
        ]
        existing_selection_summary = dict(
            selected_puzzle.metadata["composition_trace"].get("selection_summary", {})
        )
        existing_selection_summary.update(selection_summary)
        selected_puzzle.metadata["composition_trace"]["selection_summary"] = (
            existing_selection_summary
        )
        trace_recorder.add(
            "ranking",
            "Selected top puzzle candidate.",
            {
                "puzzle_id": selected_puzzle.puzzle_id,
                "passed_verification": selected_verification.passed,
                "verification_decision": selected_verification.decision.value,
                "overall_score": selected_score.overall,
                "ambiguity_risk": (
                    selected_verification.ambiguity_report.risk_level.value
                    if selected_verification.ambiguity_report is not None
                    else None
                ),
                "semantic_group_count": selected_puzzle.metadata.get("semantic_group_count", 0),
                "mechanism_mix_summary": selected_puzzle.metadata.get("mechanism_mix_summary", {}),
                "mixed_board": selected_puzzle.metadata.get("mixed_board", False),
                "composer_ranking_score": selected_puzzle.metadata.get("ranking_score", 0.0),
                "style_alignment_score": (
                    selected_score.style_analysis.board_style_summary.style_alignment_score
                    if selected_score.style_analysis is not None
                    and selected_score.style_analysis.board_style_summary is not None
                    else None
                ),
                "style_out_of_band_flags": (
                    selected_score.style_analysis.out_of_band_flags
                    if selected_score.style_analysis is not None
                    else []
                ),
                "winner_editorial_family_repeat_count": winner_editorial_family_repeat_count,
                "winner_template_repeat_count": winner_template_repeat_count,
                "winner_microtheme_repeat_count": winner_microtheme_repeat_count,
                "winner_surface_repeat_count": winner_surface_repeat_count,
            },
        )
        composition_diagnostics["winner_family_count_by_run"] = run_state[
            "winner_family_count_by_run"
        ]
        composition_diagnostics["winner_recent_history"] = run_state["winner_recent_history"]
        composition_diagnostics["winner_suppression_events"] = run_state[
            "winner_suppression_events"
        ]

        trace = (
            trace_recorder.build(
                ambiguity_report=selected_verification.ambiguity_report,
                ensemble_result=selected_verification.ensemble_result,
                style_analysis=selected_score.style_analysis,
            )
            if context.include_trace
            else None
        )
        if trace is not None:
            trace.metadata["selection_summary"] = selected_puzzle.metadata["composition_trace"][
                "selection_summary"
            ]
            trace.metadata["composition"] = composition_diagnostics
        return PipelineRunResult(
            puzzle=selected_puzzle,
            verification=selected_verification,
            score=selected_score,
            trace=trace,
            warnings=warnings,
            components=self._components,
            candidate_results=candidate_results,
            generator_diagnostics=dict(context.run_metadata.get("generator_diagnostics", {})),
            composition_diagnostics=dict(composition_diagnostics),
        )
