"""Puzzle composer implementations.

The baseline composer exists so the repository can run in demo mode. The final
quality-sensitive compatibility logic should remain human-owned and is exposed
through a separate placeholder class below.
"""

from __future__ import annotations

from abc import ABC
from collections import Counter
from itertools import combinations, product
from random import Random
from typing import ClassVar

from app.core.editorial_quality import (
    build_editorial_family_metadata,
    empty_run_family_accounting,
    ensure_run_family_accounting,
    group_earned_wordplay_score,
    group_family_signature,
    group_is_taxonomy_like_label,
    group_microtheme_smallness,
    group_phrase_template_payoff_score,
    group_surface_wordplay_score,
    polish_group_label,
    recent_winner_history_count,
    record_run_cap_hit,
    record_run_family_event,
    record_run_suppression,
    run_family_count,
)
from app.core.enums import GroupType
from app.core.stage1_quality import STAGE1_SELECTION_POLICY
from app.core.stage2_composer_policy import STAGE2_COMPOSER_POLICY
from app.core.stage3_style_policy import STAGE3_EDITORIAL_SELECTION_POLICY
from app.domain.protocols import PuzzleComposer
from app.domain.value_objects import GenerationContext
from app.features.semantic_baseline import cosine_similarity, normalize_signal
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.utils.ids import new_id, stable_id

COMPOSITION_SELECTION_POLICY = STAGE1_SELECTION_POLICY


class BasePuzzleComposer(PuzzleComposer, ABC):
    """Shared base class for puzzle composers."""

    composer_name = "base_puzzle_composer"

    @staticmethod
    def _interleave_board(groups: tuple[GroupCandidate, ...]) -> list[str]:
        board_words: list[str] = []
        for index in range(4):
            for group in groups:
                board_words.append(group.words[index])
        return board_words

    @staticmethod
    def _normalized_board_words(puzzle: PuzzleCandidate) -> set[str]:
        return {normalize_signal(word) for word in puzzle.board_words}


class BaselinePuzzleComposer(BasePuzzleComposer):
    """Compose one candidate from each group type with structural dedup checks."""

    composer_name = "baseline_puzzle_composer"

    def compose(
        self,
        groups_by_type: dict[str, list[GroupCandidate]],
        context: GenerationContext,
    ) -> list[PuzzleCandidate]:
        ordered_keys = [group_type.value for group_type in context.requested_group_types]
        candidate_lists = [list(groups_by_type.get(group_key, [])) for group_key in ordered_keys]
        if any(not candidates for candidates in candidate_lists):
            return []

        if context.seed is not None:
            rng = Random(context.seed)
            for candidates in candidate_lists:
                rng.shuffle(candidates)

        puzzles: list[PuzzleCandidate] = []
        for combination in product(*candidate_lists):
            board_words = self._interleave_board(combination)
            if len(set(board_words)) != 16:
                continue

            puzzles.append(
                PuzzleCandidate(
                    puzzle_id=new_id("puzzle"),
                    board_words=board_words,
                    groups=list(combination),
                    compatibility_notes=[
                        "Baseline composer checks only for 16 unique words across four groups.",
                        "TODO[HUMAN_HEURISTIC]: add cross-group compatibility and fairness checks.",
                    ],
                    metadata={
                        "group_types": [group.group_type.value for group in combination],
                        "baseline_only": True,
                    },
                )
            )
        return puzzles


class HumanPuzzleComposer(BasePuzzleComposer):
    """Mixed-mechanism composer baseline.

    This keeps the current `PuzzleCandidate` contract intact while moving past
    the one-group-per-type demo behavior. It searches combinations across the
    allowed candidate pool, prefers strong mixed boards when they outrank
    semantic-only fallbacks, and exposes its ranking signals directly in puzzle
    metadata.
    """

    composer_name = "human_puzzle_composer"
    _group_type_order: ClassVar[dict[str, int]] = {
        group_type.value: index for index, group_type in enumerate(GroupType.ordered())
    }

    @classmethod
    def _group_sort_key(cls, candidate: GroupCandidate) -> tuple[int, float, str, tuple[str, ...]]:
        return (
            cls._group_type_order.get(candidate.group_type.value, 99),
            -candidate.confidence,
            candidate.metadata.get("normalized_label", normalize_signal(candidate.label)),
            tuple(candidate.words),
        )

    @staticmethod
    def _mechanism_mix_summary(groups: tuple[GroupCandidate, ...]) -> dict[str, int]:
        return dict(
            sorted(
                Counter(group.group_type.value for group in groups).items(),
                key=lambda item: item[0],
            )
        )

    @staticmethod
    def _seed_family_priority(signature: str, seed: int | None) -> float:
        if seed is None:
            return 0.0
        digest = stable_id("family_seed", signature, seed).rsplit("_", 1)[-1]
        return int(digest[:8], 16) / float(16**8)

    @staticmethod
    def _run_state(context: GenerationContext) -> dict[str, object]:
        run_state = ensure_run_family_accounting(
            context.run_metadata.get("editorial_run_state", empty_run_family_accounting())
        )
        context.run_metadata["editorial_run_state"] = run_state
        return run_state

    @classmethod
    def _candidate_priority(
        cls,
        candidate: GroupCandidate,
        *,
        context: GenerationContext,
        run_state: dict[str, object],
    ) -> tuple[float, float]:
        family_signature = group_family_signature(candidate)
        priority = float(candidate.confidence)
        priority -= 0.02 * run_family_count(
            run_state,
            parent_key="family_retention_count_by_run",
            bucket="group",
            signature=family_signature,
        )
        priority -= 0.025 * recent_winner_history_count(
            run_state,
            bucket="editorial",
            signature=family_signature,
        )
        if group_surface_wordplay_score(candidate) >= 0.7:
            priority -= STAGE2_COMPOSER_POLICY.repeated_surface_family_penalty * run_family_count(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="surface",
                signature=family_signature,
            )
            priority -= 0.06 * recent_winner_history_count(
                run_state,
                bucket="surface",
                signature=family_signature,
            )
            priority -= 0.04 * max(
                0.0,
                group_surface_wordplay_score(candidate)
                - group_phrase_template_payoff_score(candidate),
            )
        if group_microtheme_smallness(candidate) >= 0.5:
            priority -= STAGE2_COMPOSER_POLICY.repeated_theme_family_penalty * run_family_count(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="theme",
                signature=family_signature,
            )
            priority -= 0.08 * recent_winner_history_count(
                run_state,
                bucket="theme",
                signature=family_signature,
            )
        seed_priority = cls._seed_family_priority(family_signature, context.seed)
        priority += 0.04 * (seed_priority - 0.5)
        return (round(priority, 6), seed_priority)

    @classmethod
    def _candidate_pool(
        cls,
        groups_by_type: dict[str, list[GroupCandidate]],
        context: GenerationContext,
    ) -> tuple[list[GroupCandidate], dict[str, int]]:
        allowed_types = [group_type.value for group_type in context.requested_group_types]
        run_state = cls._run_state(context)
        pool: list[GroupCandidate] = []
        counts: dict[str, int] = {}
        for group_type in allowed_types:
            ranked = sorted(
                groups_by_type.get(group_type, []),
                key=lambda candidate: (
                    -cls._candidate_priority(candidate, context=context, run_state=run_state)[0],
                    cls._group_sort_key(candidate),
                ),
            )
            retained_per_family: Counter[str] = Counter()
            trimmed: list[GroupCandidate] = []
            for candidate in ranked:
                family_signature = group_family_signature(candidate)
                if (
                    retained_per_family[family_signature]
                    >= STAGE2_COMPOSER_POLICY.max_group_candidates_per_family
                ):
                    record_run_suppression(
                        run_state,
                        reason="candidate_pool_family_trim",
                        signature=family_signature,
                    )
                    record_run_cap_hit(
                        run_state,
                        bucket="group",
                        signature=family_signature,
                    )
                    continue
                trimmed.append(candidate)
                retained_per_family[family_signature] += 1
                if len(trimmed) >= STAGE2_COMPOSER_POLICY.max_candidates_per_type:
                    break
            counts[group_type] = len(trimmed)
            pool.extend(trimmed)
        return pool, counts

    @staticmethod
    def _cross_group_similarity(groups: tuple[GroupCandidate, ...]) -> float:
        centroids = [
            [float(value) for value in group.metadata.get("semantic_centroid", [])]
            for group in groups
            if group.metadata.get("semantic_centroid")
        ]
        if len(centroids) < 2:
            return 0.0

        similarities = [
            cosine_similarity(centroids[left_index], centroids[right_index])
            for left_index in range(len(centroids))
            for right_index in range(left_index + 1, len(centroids))
        ]
        return sum(similarities) / len(similarities) if similarities else 0.0

    @staticmethod
    def _mechanism_redundancy_penalty(groups: tuple[GroupCandidate, ...]) -> float:
        type_counts = Counter(group.group_type.value for group in groups)
        repeated_type_penalty = 0.02 * sum(max(0, count - 1) for count in type_counts.values())

        lexical_pattern_counts = Counter(
            group.metadata.get("pattern_type")
            for group in groups
            if group.group_type is GroupType.LEXICAL and group.metadata.get("pattern_type")
        )
        repeated_lexical_penalty = 0.03 * sum(
            max(0, count - 1) for count in lexical_pattern_counts.values()
        )
        return round(repeated_type_penalty + repeated_lexical_penalty, 4)

    @staticmethod
    def _diversity_bonus(groups: tuple[GroupCandidate, ...]) -> float:
        editorial_metadata = build_editorial_family_metadata(groups)
        bonus = 0.0
        if bool(editorial_metadata.get("semantic_majority_board")):
            bonus += STAGE2_COMPOSER_POLICY.semantic_majority_bonus
        elif (
            len({group.group_type.value for group in groups}) >= 3
            and not bool(editorial_metadata.get("balanced_mixed_board"))
            and int(editorial_metadata.get("wordplay_group_count", 0)) <= 1
        ):
            bonus += 0.015
        if any(group_earned_wordplay_score(group) >= 0.8 for group in groups):
            bonus += 0.01
        if any(
            group.group_type is GroupType.THEME and group_microtheme_smallness(group) < 0.5
            for group in groups
        ):
            bonus += 0.005
        return round(bonus, 4)

    @staticmethod
    def _source_precision_bonus(groups: tuple[GroupCandidate, ...]) -> float:
        bonus = 0.0
        for group in groups:
            if group.group_type is GroupType.PHONETIC and group_earned_wordplay_score(group) >= 0.8:
                bonus += 0.03
            if (
                group.group_type is GroupType.THEME
                and group_microtheme_smallness(group) < 0.5
                and group_phrase_template_payoff_score(group) >= 0.35
            ):
                bonus += 0.015
        return round(bonus, 4)

    @staticmethod
    def _polished_groups(groups: tuple[GroupCandidate, ...]) -> tuple[GroupCandidate, ...]:
        return tuple(polish_group_label(group) for group in groups)

    @classmethod
    def _combination_score(
        cls,
        groups: tuple[GroupCandidate, ...],
        editorial_metadata: dict[str, object],
        *,
        run_state: dict[str, object],
    ) -> tuple[float, ...]:
        semantic_group_count = sum(1 for group in groups if group.group_type is GroupType.SEMANTIC)
        confidence_total = round(sum(group.confidence for group in groups), 4)
        cross_group_similarity = HumanPuzzleComposer._cross_group_similarity(groups)
        diversity_bonus = cls._diversity_bonus(groups)
        source_precision_bonus = cls._source_precision_bonus(groups)
        redundancy_penalty = cls._mechanism_redundancy_penalty(groups)
        surface_wordplay_penalty = round(
            0.065
            * sum(
                max(
                    0.0,
                    group_surface_wordplay_score(group)
                    - max(0.12, 0.25 * group_phrase_template_payoff_score(group)),
                )
                for group in groups
                if group_surface_wordplay_score(group) >= 0.7
            ),
            4,
        )
        microtheme_penalty = round(
            0.17
            * sum(
                group_microtheme_smallness(group)
                for group in groups
                if group.group_type is GroupType.THEME
            ),
            4,
        )
        repeated_pattern_penalty = round(
            0.08 * max(0, len(editorial_metadata["low_payoff_surface_wordplay_families"]) - 1),
            4,
        )
        low_payoff_pattern_penalty = round(
            0.12
            * sum(
                max(
                    0.0,
                    group_surface_wordplay_score(group) - group_phrase_template_payoff_score(group),
                )
                for group in groups
                if group.group_type in {GroupType.LEXICAL, GroupType.PHONETIC}
            ),
            4,
        )
        formulaic_mix_penalty = round(
            STAGE2_COMPOSER_POLICY.balanced_mixed_penalty
            if "formulaic_mixed_template" in editorial_metadata["editorial_flags"]
            else 0.0,
            4,
        )
        balanced_mixed_penalty = round(
            STAGE2_COMPOSER_POLICY.balanced_mixed_penalty
            if bool(editorial_metadata.get("balanced_mixed_board"))
            else 0.0,
            4,
        )
        microtheme_plus_wordplay_penalty = round(
            STAGE2_COMPOSER_POLICY.microtheme_plus_wordplay_penalty
            if bool(editorial_metadata.get("microtheme_plus_wordplay"))
            else 0.0,
            4,
        )
        semantic_majority_bonus = round(
            STAGE2_COMPOSER_POLICY.semantic_majority_bonus
            if bool(editorial_metadata.get("semantic_majority_board"))
            else 0.0,
            4,
        )
        clue_payoff_bonus = round(
            0.025
            * sum(
                group_phrase_template_payoff_score(group) >= 0.75
                and group_phrase_template_payoff_score(group)
                >= group_surface_wordplay_score(group)
                for group in groups
            ),
            4,
        )
        taxonomy_label_penalty = round(
            0.035 * sum(group_is_taxonomy_like_label(group) for group in groups),
            4,
        )
        semantic_sparse_penalty = round(
            0.18
            if (
                semantic_group_count <= 1
                and bool(editorial_metadata.get("microtheme_plus_wordplay"))
            )
            else (
                0.09
                if semantic_group_count <= 1
                and int(editorial_metadata.get("wordplay_group_count", 0)) >= 1
                else 0.0
            ),
            4,
        )
        editorial_repeat_count = run_family_count(
            run_state,
            parent_key="family_retention_count_by_run",
            bucket="editorial",
            signature=str(editorial_metadata.get("editorial_family_signature")),
        )
        template_repeat_count = run_family_count(
            run_state,
            parent_key="family_retention_count_by_run",
            bucket="template",
            signature=str(editorial_metadata.get("mechanism_template_signature")),
        )
        theme_repeat_count = max(
            (
                run_family_count(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="theme",
                    signature=str(signature),
                )
                for signature in list(editorial_metadata.get("microtheme_family_signatures", []))
            ),
            default=0,
        )
        surface_repeat_count = max(
            (
                run_family_count(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="surface",
                    signature=str(signature),
                )
                for signature in list(
                    editorial_metadata.get("surface_wordplay_family_signatures", [])
                )
            ),
            default=0,
        )
        run_family_penalty = round(
            (STAGE2_COMPOSER_POLICY.repeated_editorial_family_penalty * editorial_repeat_count)
            + (STAGE2_COMPOSER_POLICY.repeated_template_penalty * template_repeat_count)
            + (
                STAGE2_COMPOSER_POLICY.repeated_theme_family_penalty * theme_repeat_count
                if list(editorial_metadata.get("microtheme_family_signatures", []))
                else 0.0
            )
            + (
                STAGE2_COMPOSER_POLICY.repeated_surface_family_penalty * surface_repeat_count
                if list(editorial_metadata.get("surface_wordplay_family_signatures", []))
                else 0.0
            ),
            4,
        )
        winner_history_penalty = round(
            (0.08 * recent_winner_history_count(
                run_state,
                bucket="editorial",
                signature=str(editorial_metadata.get("editorial_family_signature")),
            ))
            + (0.06 * recent_winner_history_count(
                run_state,
                bucket="template",
                signature=str(editorial_metadata.get("mechanism_template_signature")),
            ))
            + (
                0.09
                * max(
                    (
                        recent_winner_history_count(
                            run_state,
                            bucket="theme",
                            signature=str(signature),
                        )
                        for signature in list(
                            editorial_metadata.get("microtheme_family_signatures", [])
                        )
                    ),
                    default=0,
                )
            )
            + (
                0.08
                * max(
                    (
                        recent_winner_history_count(
                            run_state,
                            bucket="surface",
                            signature=str(signature),
                        )
                        for signature in list(
                            editorial_metadata.get("surface_wordplay_family_signatures", [])
                        )
                    ),
                    default=0,
                )
            ),
            4,
        )
        ranking_score = round(
            (
                confidence_total
                + diversity_bonus
                + semantic_majority_bonus
                + source_precision_bonus
                + clue_payoff_bonus
                - (0.3 * cross_group_similarity)
                - redundancy_penalty
                - formulaic_mix_penalty
                - balanced_mixed_penalty
                - surface_wordplay_penalty
                - microtheme_penalty
                - repeated_pattern_penalty
                - low_payoff_pattern_penalty
                - microtheme_plus_wordplay_penalty
                - run_family_penalty
                - taxonomy_label_penalty
                - semantic_sparse_penalty
                - winner_history_penalty
            ),
            4,
        )
        return (
            ranking_score,
            round(cross_group_similarity, 4),
            semantic_group_count,
            confidence_total,
            diversity_bonus,
            source_precision_bonus,
            redundancy_penalty,
            formulaic_mix_penalty,
            surface_wordplay_penalty,
            microtheme_penalty,
            repeated_pattern_penalty,
            low_payoff_pattern_penalty,
            semantic_majority_bonus,
            clue_payoff_bonus,
            taxonomy_label_penalty,
            semantic_sparse_penalty,
            balanced_mixed_penalty,
            run_family_penalty,
        )

    @staticmethod
    def _deferred_fill_key(
        puzzle: PuzzleCandidate,
        *,
        run_state: dict[str, object],
    ) -> tuple[float, ...] | tuple[int, float, str]:
        return (
            recent_winner_history_count(
                run_state,
                bucket="editorial",
                signature=str(puzzle.metadata.get("editorial_family_signature")),
            ),
            recent_winner_history_count(
                run_state,
                bucket="template",
                signature=str(puzzle.metadata.get("mechanism_template_signature")),
            ),
            max(
                (
                    recent_winner_history_count(
                        run_state,
                        bucket="theme",
                        signature=str(signature),
                    )
                    for signature in puzzle.metadata.get("theme_family_signatures", [])
                ),
                default=0,
            ),
            max(
                (
                    recent_winner_history_count(
                        run_state,
                        bucket="surface",
                        signature=str(signature),
                    )
                    for signature in puzzle.metadata.get("surface_wordplay_family_signatures", [])
                ),
                default=0,
            ),
            -int(bool(puzzle.metadata.get("semantic_majority_board", False))),
            int(bool(puzzle.metadata.get("balanced_mixed_board", False))),
            int(bool(puzzle.metadata.get("microtheme_plus_wordplay", False))),
            float(puzzle.metadata.get("surface_wordplay_penalty", 0.0)),
            float(puzzle.metadata.get("microtheme_penalty", 0.0)),
            -float(puzzle.metadata.get("clue_payoff_bonus", 0.0)),
            -float(puzzle.metadata.get("ranking_score", 0.0)),
            puzzle.puzzle_id,
        )

    @classmethod
    def _ordered_groups(cls, groups: tuple[GroupCandidate, ...]) -> tuple[GroupCandidate, ...]:
        return tuple(sorted(groups, key=cls._group_sort_key))

    @staticmethod
    def _overlapping_word_ids(groups: tuple[GroupCandidate, ...]) -> list[str]:
        counts = Counter(word_id for group in groups for word_id in group.word_ids)
        return sorted(word_id for word_id, count in counts.items() if count > 1)

    @staticmethod
    def _family_diversity_allowed(
        puzzle: PuzzleCandidate,
        selected: list[PuzzleCandidate],
        *,
        run_state: dict[str, object],
    ) -> tuple[bool, str | None, str | None]:
        editorial_family_signature = puzzle.metadata.get("editorial_family_signature")
        theme_family_signatures = set(puzzle.metadata.get("theme_family_signatures", []))
        surface_wordplay_family_signatures = set(
            puzzle.metadata.get("surface_wordplay_family_signatures", [])
        )
        editorial_flags = set(puzzle.metadata.get("editorial_flags", []))
        template_signature = puzzle.metadata.get("mechanism_template_signature")

        if editorial_family_signature and (
            sum(
                existing.metadata.get("editorial_family_signature") == editorial_family_signature
                for existing in selected
            )
            >= STAGE3_EDITORIAL_SELECTION_POLICY.composer_editorial_family_cap
        ):
            return False, "composer_editorial_family_cap", str(editorial_family_signature)

        if "microtheme_trivia_smallness" in editorial_flags:
            for signature in theme_family_signatures:
                if (
                    sum(
                        signature in set(existing.metadata.get("theme_family_signatures", []))
                        for existing in selected
                    )
                    >= STAGE3_EDITORIAL_SELECTION_POLICY.composer_theme_family_cap
                ):
                    return False, "composer_theme_family_cap", str(signature)

        for signature in surface_wordplay_family_signatures:
            if (
                sum(
                    signature
                    in set(existing.metadata.get("surface_wordplay_family_signatures", []))
                    for existing in selected
                )
                >= STAGE3_EDITORIAL_SELECTION_POLICY.composer_surface_wordplay_family_cap
            ):
                return False, "composer_surface_wordplay_family_cap", str(signature)

        if editorial_family_signature and (
            run_family_count(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="editorial",
                signature=str(editorial_family_signature),
            )
            >= STAGE2_COMPOSER_POLICY.run_editorial_family_cap
        ):
            return False, "run_editorial_family_cap", str(editorial_family_signature)

        for signature in theme_family_signatures:
            if (
                run_family_count(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="theme",
                    signature=str(signature),
                )
                >= STAGE2_COMPOSER_POLICY.run_small_theme_family_cap
            ):
                return False, "run_small_theme_family_cap", str(signature)

        for signature in surface_wordplay_family_signatures:
            if (
                run_family_count(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="surface",
                    signature=str(signature),
                )
                >= STAGE2_COMPOSER_POLICY.run_surface_wordplay_family_cap
            ):
                return False, "run_surface_wordplay_family_cap", str(signature)

        if bool(puzzle.metadata.get("balanced_mixed_board")) and template_signature and (
            run_family_count(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="template",
                signature=str(template_signature),
            )
            >= STAGE2_COMPOSER_POLICY.run_balanced_mixed_template_cap
        ):
            return False, "run_balanced_mixed_template_cap", str(template_signature)

        return True, None, None

    def compose(
        self,
        groups_by_type: dict[str, list[GroupCandidate]],
        context: GenerationContext,
    ) -> list[PuzzleCandidate]:
        run_state = self._run_state(context)
        pool, candidate_pool_by_type = self._candidate_pool(groups_by_type, context)
        diagnostics: dict[str, object] = {
            "composer": self.composer_name,
            "candidate_pool_size": len(pool),
            "candidate_pool_by_type": candidate_pool_by_type,
            "selection_policy": COMPOSITION_SELECTION_POLICY,
            "rejected_combinations": [],
            "rejected_combination_reason_counts": {},
            "failure_reasons": [],
        }

        if len(pool) < 4:
            diagnostics["failure_reasons"] = ["insufficient_candidate_pool"]
            context.run_metadata["composition_diagnostics"] = diagnostics
            return []

        deduped_pool: dict[tuple[str, tuple[str, ...]], GroupCandidate] = {}
        for candidate in pool:
            key = (candidate.group_type.value, tuple(sorted(candidate.word_ids)))
            current = deduped_pool.get(key)
            if current is None or candidate.confidence > current.confidence:
                deduped_pool[key] = candidate

        diagnostics["deduped_candidate_count"] = len(deduped_pool)
        ranked_puzzles: list[tuple[tuple[float, float, int, tuple[str, ...]], PuzzleCandidate]] = []
        rejected_combinations: list[dict[str, object]] = []
        rejected_combination_reason_counts: Counter[str] = Counter()
        evaluated_combinations = 0

        for combination in combinations(sorted(deduped_pool.values(), key=self._group_sort_key), 4):
            ordered_groups = self._ordered_groups(combination)
            polished_groups = self._polished_groups(ordered_groups)
            overlapping_word_ids = self._overlapping_word_ids(ordered_groups)
            if overlapping_word_ids:
                rejected_combination_reason_counts["overlapping_words"] += 1
                if len(rejected_combinations) < STAGE2_COMPOSER_POLICY.max_rejected_combinations:
                    rejected_combinations.append(
                        {
                            "candidate_ids": [group.candidate_id for group in ordered_groups],
                            "reason": "overlapping_words",
                            "overlapping_word_ids": overlapping_word_ids,
                        }
                    )
                continue

            evaluated_combinations += 1
            board_words = self._interleave_board(polished_groups)
            editorial_metadata = build_editorial_family_metadata(polished_groups)
            (
                ranking_score,
                cross_group_similarity,
                semantic_group_count,
                confidence_total,
                diversity_bonus,
                source_precision_bonus,
                redundancy_penalty,
                formulaic_mix_penalty,
                surface_wordplay_penalty,
                microtheme_penalty,
                repeated_pattern_penalty,
                low_payoff_pattern_penalty,
                semantic_majority_bonus,
                clue_payoff_bonus,
                taxonomy_label_penalty,
                semantic_sparse_penalty,
                balanced_mixed_penalty,
                run_family_penalty,
            ) = self._combination_score(
                polished_groups,
                editorial_metadata,
                run_state=run_state,
            )
            for signature in editorial_metadata["group_family_signatures"]:
                record_run_family_event(
                    run_state,
                    parent_key="family_proposal_count_by_run",
                    bucket="group",
                    signature=str(signature),
                )
            record_run_family_event(
                run_state,
                parent_key="family_proposal_count_by_run",
                bucket="board",
                signature=str(editorial_metadata["board_family_signature"]),
            )
            record_run_family_event(
                run_state,
                parent_key="family_proposal_count_by_run",
                bucket="editorial",
                signature=str(editorial_metadata["editorial_family_signature"]),
            )
            record_run_family_event(
                run_state,
                parent_key="family_proposal_count_by_run",
                bucket="template",
                signature=str(editorial_metadata["mechanism_template_signature"]),
            )
            for signature in editorial_metadata["theme_family_signatures"]:
                record_run_family_event(
                    run_state,
                    parent_key="family_proposal_count_by_run",
                    bucket="theme",
                    signature=str(signature),
                )
            for signature in editorial_metadata["surface_wordplay_family_signatures"]:
                record_run_family_event(
                    run_state,
                    parent_key="family_proposal_count_by_run",
                    bucket="surface",
                    signature=str(signature),
                )
            group_types = [group.group_type.value for group in ordered_groups]
            mechanism_mix_summary = self._mechanism_mix_summary(ordered_groups)
            mixed_board = len(mechanism_mix_summary) > 1
            composition_trace = {
                "composer": self.composer_name,
                "candidate_pool_size": len(pool),
                "candidate_pool_by_type": candidate_pool_by_type,
                "deduped_candidate_count": len(deduped_pool),
                "evaluated_combination_count": evaluated_combinations,
                "selected_candidate_ids": [group.candidate_id for group in polished_groups],
                "selected_group_labels": [group.label for group in polished_groups],
                "rejected_combinations": rejected_combinations[
                    : STAGE2_COMPOSER_POLICY.max_rejected_combinations
                ],
                "selection_summary": {
                    "semantic_group_count": semantic_group_count,
                    "mixed_board": mixed_board,
                    "mechanism_mix_summary": mechanism_mix_summary,
                    "confidence_total": confidence_total,
                    "cross_group_similarity": cross_group_similarity,
                    "diversity_bonus": diversity_bonus,
                    "semantic_majority_bonus": semantic_majority_bonus,
                    "clue_payoff_bonus": clue_payoff_bonus,
                    "source_precision_bonus": source_precision_bonus,
                    "mechanism_redundancy_penalty": redundancy_penalty,
                    "formulaic_mix_penalty": formulaic_mix_penalty,
                    "balanced_mixed_penalty": balanced_mixed_penalty,
                    "surface_wordplay_penalty": surface_wordplay_penalty,
                    "microtheme_penalty": microtheme_penalty,
                    "repeated_pattern_family_penalty": repeated_pattern_penalty,
                    "low_payoff_pattern_penalty": low_payoff_pattern_penalty,
                    "taxonomy_label_penalty": taxonomy_label_penalty,
                    "semantic_sparse_penalty": semantic_sparse_penalty,
                    "run_family_penalty": run_family_penalty,
                    "composer_ranking_score": ranking_score,
                },
            }

            puzzle = PuzzleCandidate(
                puzzle_id=stable_id(
                    "puzzle",
                    tuple(group.candidate_id for group in polished_groups),
                ),
                board_words=board_words,
                groups=list(polished_groups),
                compatibility_notes=[
                    (
                        "Semantic baseline composer ranks boards using group "
                        "confidence and centroid similarity."
                    ),
                    (
                        "This is a transparent baseline rather than the "
                        "final editorial compatibility policy."
                    ),
                ],
                metadata={
                    "group_types": group_types,
                    "semantic_group_count": semantic_group_count,
                    "semantic_majority_board": bool(editorial_metadata["semantic_majority_board"]),
                    "balanced_mixed_board": bool(editorial_metadata["balanced_mixed_board"]),
                    "mixed_board": mixed_board,
                    "mechanism_mix_summary": mechanism_mix_summary,
                    "mechanism_mix_signature": "+".join(sorted(mechanism_mix_summary)),
                    "mechanism_template_signature": editorial_metadata[
                        "mechanism_template_signature"
                    ],
                    "unique_group_type_count": len(mechanism_mix_summary),
                    "cross_group_similarity": cross_group_similarity,
                    "ranking_score": ranking_score,
                    "confidence_total": confidence_total,
                    "diversity_bonus": diversity_bonus,
                    "semantic_majority_bonus": semantic_majority_bonus,
                    "clue_payoff_bonus": clue_payoff_bonus,
                    "source_precision_bonus": source_precision_bonus,
                    "mechanism_redundancy_penalty": redundancy_penalty,
                    "formulaic_mix_penalty": formulaic_mix_penalty,
                    "balanced_mixed_penalty": balanced_mixed_penalty,
                    "surface_wordplay_penalty": surface_wordplay_penalty,
                    "microtheme_penalty": microtheme_penalty,
                    "repeated_pattern_family_penalty": repeated_pattern_penalty,
                    "low_payoff_pattern_penalty": low_payoff_pattern_penalty,
                    "taxonomy_label_penalty": taxonomy_label_penalty,
                    "semantic_sparse_penalty": semantic_sparse_penalty,
                    "run_family_penalty": run_family_penalty,
                    **editorial_metadata,
                    "baseline_mode": "mixed_mechanism_composer",
                    "composition_trace": composition_trace,
                },
            )
            ranked_puzzles.append(
                (
                    (
                        ranking_score,
                        confidence_total,
                        semantic_group_count,
                        tuple(group.label for group in polished_groups),
                    ),
                    puzzle,
                )
            )

        diagnostics["evaluated_combination_count"] = evaluated_combinations
        diagnostics["rejected_combinations"] = rejected_combinations
        diagnostics["rejected_combination_reason_counts"] = dict(
            sorted(rejected_combination_reason_counts.items())
        )
        if not ranked_puzzles:
            diagnostics["failure_reasons"] = ["insufficient_non_overlapping_groups"]
            context.run_metadata["composition_diagnostics"] = diagnostics
            return []

        ranked = sorted(
            ranked_puzzles,
            key=lambda item: (
                -item[0][0],
                -item[0][1],
                -item[0][2],
                item[0][3],
            ),
        )
        top_ranked: list[PuzzleCandidate] = []
        deferred_ranked: list[PuzzleCandidate] = []
        near_duplicate_skips = 0
        family_diversity_skips = 0
        for _, puzzle in ranked:
            puzzle_words = self._normalized_board_words(puzzle)
            if any(
                len(puzzle_words & self._normalized_board_words(existing))
                >= STAGE2_COMPOSER_POLICY.near_duplicate_board_overlap_threshold
                for existing in top_ranked
            ):
                near_duplicate_skips += 1
                continue
            allowed, reason, signature = self._family_diversity_allowed(
                puzzle,
                top_ranked,
                run_state=run_state,
            )
            if not allowed:
                family_diversity_skips += 1
                record_run_suppression(run_state, reason=str(reason), signature=signature)
                record_run_cap_hit(run_state, bucket=str(reason), signature=signature)
                deferred_ranked.append(puzzle)
                continue
            top_ranked.append(puzzle)
            if len(top_ranked) >= STAGE2_COMPOSER_POLICY.max_ranked_puzzles:
                break
        if not top_ranked:
            top_ranked = [
                puzzle for _, puzzle in ranked[: STAGE2_COMPOSER_POLICY.max_ranked_puzzles]
            ]
        elif len(top_ranked) < STAGE2_COMPOSER_POLICY.max_ranked_puzzles:
            for puzzle in sorted(
                deferred_ranked,
                key=lambda item: self._deferred_fill_key(item, run_state=run_state),
            ):
                if puzzle in top_ranked:
                    continue
                puzzle_words = self._normalized_board_words(puzzle)
                if any(
                    len(puzzle_words & self._normalized_board_words(existing))
                    >= STAGE2_COMPOSER_POLICY.near_duplicate_board_overlap_threshold
                    for existing in top_ranked
                ):
                    continue
                top_ranked.append(puzzle)
                if len(top_ranked) >= STAGE2_COMPOSER_POLICY.max_ranked_puzzles:
                    break
        for puzzle in top_ranked:
            for signature in puzzle.metadata.get("group_family_signatures", []):
                record_run_family_event(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="group",
                    signature=str(signature),
                )
            record_run_family_event(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="board",
                signature=str(puzzle.metadata.get("board_family_signature")),
            )
            record_run_family_event(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="editorial",
                signature=str(puzzle.metadata.get("editorial_family_signature")),
            )
            record_run_family_event(
                run_state,
                parent_key="family_retention_count_by_run",
                bucket="template",
                signature=str(puzzle.metadata.get("mechanism_template_signature")),
            )
            for signature in puzzle.metadata.get("theme_family_signatures", []):
                record_run_family_event(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="theme",
                    signature=str(signature),
                )
            for signature in puzzle.metadata.get("surface_wordplay_family_signatures", []):
                record_run_family_event(
                    run_state,
                    parent_key="family_retention_count_by_run",
                    bucket="surface",
                    signature=str(signature),
                )
        selected_signatures = [
            puzzle.metadata["composition_trace"]["selected_candidate_ids"] for puzzle in top_ranked
        ]
        best_mixed = next((puzzle for puzzle in top_ranked if puzzle.metadata["mixed_board"]), None)
        best_semantic_only = next(
            (puzzle for puzzle in top_ranked if not puzzle.metadata["mixed_board"]),
            None,
        )
        diagnostics["selected_candidate_signatures"] = selected_signatures
        diagnostics["near_duplicate_ranked_skip_count"] = near_duplicate_skips
        diagnostics["family_diversity_skip_count"] = family_diversity_skips
        diagnostics["family_proposal_count_by_run"] = run_state["family_proposal_count_by_run"]
        diagnostics["family_retention_count_by_run"] = run_state["family_retention_count_by_run"]
        diagnostics["family_suppression_events"] = run_state["family_suppression_events"]
        diagnostics["per_family_cap_hits"] = run_state["per_family_cap_hits"]
        diagnostics["best_mixed_candidate"] = (
            {
                "puzzle_id": best_mixed.puzzle_id,
                "mechanism_mix_summary": best_mixed.metadata["mechanism_mix_summary"],
                "ranking_score": best_mixed.metadata["ranking_score"],
            }
            if best_mixed is not None
            else None
        )
        diagnostics["best_semantic_only_candidate"] = (
            {
                "puzzle_id": best_semantic_only.puzzle_id,
                "mechanism_mix_summary": best_semantic_only.metadata["mechanism_mix_summary"],
                "ranking_score": best_semantic_only.metadata["ranking_score"],
            }
            if best_semantic_only is not None
            else None
        )
        context.run_metadata["composition_diagnostics"] = diagnostics
        return top_ranked
