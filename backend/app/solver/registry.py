"""Registry helpers for solver adapters.

The registry provides thin dependency management for baseline and future
human-owned solver backends. It is intentionally small so orchestration stays
decoupled from concrete solver construction.
"""

from __future__ import annotations

from app.solver.base import SolverAdapter
from app.solver.mock_solver import MockSolverBackend
from app.solver.simple_heuristic_solver import SimpleHeuristicSolverBackend


class SolverRegistry:
    """Registry of solver adapters keyed by backend name."""

    def __init__(self) -> None:
        self._solvers: dict[str, SolverAdapter] = {}

    def register(self, solver: SolverAdapter) -> None:
        self._solvers[solver.backend_name] = solver

    def list_solvers(self) -> list[SolverAdapter]:
        return list(self._solvers.values())

    def names(self) -> list[str]:
        return list(self._solvers.keys())


def build_demo_solver_registry() -> SolverRegistry:
    """Return the default demo registry with 2 baseline solvers."""

    registry = SolverRegistry()
    registry.register(MockSolverBackend())
    registry.register(SimpleHeuristicSolverBackend())
    return registry
