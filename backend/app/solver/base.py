"""Base classes for solver and verification components."""

from __future__ import annotations

from abc import ABC

from app.domain.protocols import AmbiguityEvaluator, PuzzleVerifier, SolverBackend


class BaseSolverBackend(SolverBackend, ABC):
    """Convenience base class for solver adapters."""

    backend_name = "base_solver_backend"


class BasePuzzleVerifier(PuzzleVerifier, ABC):
    """Convenience base class for verification components."""

    verifier_name = "base_puzzle_verifier"


class BaseAmbiguityEvaluator(AmbiguityEvaluator, ABC):
    """Convenience base class for ambiguity evaluators."""

    evaluator_name = "base_ambiguity_evaluator"
