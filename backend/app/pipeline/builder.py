"""Puzzle composer implementations.

The baseline composer exists so the repository can run in demo mode. The final
quality-sensitive compatibility logic should remain human-owned and is exposed
through a separate placeholder class below.
"""

from __future__ import annotations

from abc import ABC
from itertools import product
from random import Random

from app.domain.protocols import PuzzleComposer
from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import GroupCandidate, PuzzleCandidate
from app.utils.ids import new_id


class BasePuzzleComposer(PuzzleComposer, ABC):
    """Shared base class for puzzle composers."""

    composer_name = "base_puzzle_composer"


class BaselinePuzzleComposer(BasePuzzleComposer):
    """Compose one candidate from each group type with structural dedup checks."""

    composer_name = "baseline_puzzle_composer"

    @staticmethod
    def _interleave_board(groups: tuple[GroupCandidate, ...]) -> list[str]:
        board_words: list[str] = []
        for index in range(4):
            for group in groups:
                board_words.append(group.words[index])
        return board_words

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
    """Placeholder for the final human-owned puzzle composition strategy.

    File location:
        backend/app/pipeline/builder.py

    Inputs:
        - Candidate groups from all generator families.

    Outputs:
        - Ranked `PuzzleCandidate` objects with compatibility metadata.

    TODO[HUMAN_CORE]:
        Implement composition logic that reasons about cross-group interference,
        leakage, freshness, and style.

    TODO[HUMAN_HEURISTIC]:
        Define compatibility checks that reject puzzles with suspicious overlap
        even when the words are technically unique.

    Acceptance criteria:
        - Produces structurally valid 16-word puzzles.
        - Surfaces compatibility diagnostics for verifier and scorer use.
        - Avoids baking NYT-like quality assumptions into opaque magic numbers.
    """

    composer_name = "human_puzzle_composer"

    def compose(
        self,
        groups_by_type: dict[str, list[GroupCandidate]],
        context: GenerationContext,
    ) -> list[PuzzleCandidate]:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement human-owned puzzle composition logic."
        )
