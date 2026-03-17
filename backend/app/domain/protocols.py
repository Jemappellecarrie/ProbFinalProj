"""Abstract contracts for the puzzle generation system."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.value_objects import GenerationContext
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import (
    GroupCandidate,
    PuzzleCandidate,
    PuzzleScore,
    SolverResult,
    VerificationResult,
)


class WordRepository(ABC):
    """Source of normalized seed words."""

    @abstractmethod
    def list_entries(self) -> list[WordEntry]:
        raise NotImplementedError


class WordFeatureExtractor(ABC):
    """Transforms raw words into structured feature records."""

    extractor_name: str = "abstract_feature_extractor"

    @abstractmethod
    def extract_features(self, words: list[WordEntry]) -> list[WordFeatures]:
        raise NotImplementedError


class GroupGenerator(ABC):
    """Produces four-word candidate groups for a specific grouping family."""

    strategy_name: str = "abstract_group_generator"

    @abstractmethod
    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        raise NotImplementedError


class PuzzleComposer(ABC):
    """Combines candidate groups into a 16-word puzzle candidate."""

    composer_name: str = "abstract_puzzle_composer"

    @abstractmethod
    def compose(
        self,
        groups_by_type: dict[str, list[GroupCandidate]],
        context: GenerationContext,
    ) -> list[PuzzleCandidate]:
        raise NotImplementedError


class SolverBackend(ABC):
    """External or internal solver adapter used during verification."""

    backend_name: str = "abstract_solver_backend"

    @abstractmethod
    def solve(self, puzzle: PuzzleCandidate, context: GenerationContext) -> SolverResult:
        raise NotImplementedError


class AmbiguityEvaluator(ABC):
    """Estimates ambiguity or leakage based on solver output."""

    evaluator_name: str = "abstract_ambiguity_evaluator"

    @abstractmethod
    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
    ) -> VerificationResult:
        raise NotImplementedError


class PuzzleVerifier(ABC):
    """Validates candidate puzzles against structural and solver-based checks."""

    verifier_name: str = "abstract_puzzle_verifier"

    @abstractmethod
    def verify(self, puzzle: PuzzleCandidate, context: GenerationContext) -> VerificationResult:
        raise NotImplementedError


class PuzzleScorer(ABC):
    """Assigns interpretable scores to verified puzzle candidates."""

    scorer_name: str = "abstract_puzzle_scorer"

    @abstractmethod
    def score(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> PuzzleScore:
        raise NotImplementedError
