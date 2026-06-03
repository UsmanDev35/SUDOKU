"""Solver implementations and manager facade.

Contains four solver strategies: Backtracking, Informed (AC-3 + MRV),
Simulated Annealing, and Forward Checking with Constraint Propagation.
The SolverManager facade registers all solvers and routes solve requests
to the appropriate implementation by SolverType.
"""

from __future__ import annotations

from typing import Generator

from sudoku_solver_evaluator.models.enums import SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol
from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver
from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver
from sudoku_solver_evaluator.solvers.informed import InformedSolver
from sudoku_solver_evaluator.solvers.simulated_annealing import SimulatedAnnealingSolver


class SolverManager:
    """Manages solver instances and dispatches solve requests.

    Acts as a facade that routes solve requests to the appropriate solver
    implementation based on the requested SolverType. All four solvers are
    registered on initialization.

    Attributes:
        _solvers: Mapping of SolverType to solver implementation instances.
    """

    def __init__(self) -> None:
        """Initialize the SolverManager and register all solver implementations."""
        self._solvers: dict[SolverType, SolverProtocol] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all four built-in solver implementations."""
        self.register(SolverType.BACKTRACKING, BacktrackingSolver())
        self.register(SolverType.INFORMED, InformedSolver())
        self.register(SolverType.LOCAL_SEARCH, SimulatedAnnealingSolver())
        self.register(SolverType.FORWARD_CHECKING, ForwardCheckingSolver())

    def register(self, solver_type: SolverType, solver: SolverProtocol) -> None:
        """Register a solver implementation for a given solver type.

        Args:
            solver_type: The SolverType enum value to associate with the solver.
            solver: A solver instance implementing SolverProtocol.

        Raises:
            TypeError: If solver does not implement SolverProtocol.
        """
        if not isinstance(solver, SolverProtocol):
            raise TypeError(
                f"Solver must implement SolverProtocol, got {type(solver).__name__}"
            )
        self._solvers[solver_type] = solver

    def solve(
        self, grid: Grid, solver_type: SolverType, timeout: float = 60.0
    ) -> SolveResult:
        """Solve a puzzle using the specified solver.

        Routes the solve request to the appropriate solver implementation
        based on the solver_type parameter.

        Args:
            grid: The initial puzzle grid (not mutated).
            solver_type: Which solver algorithm to use.
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Returns:
            SolveResult containing the solution (if found), metrics, and status.

        Raises:
            ValueError: If no solver is registered for the given solver_type.
        """
        solver = self._get_solver(solver_type)
        return solver.solve(grid, timeout=timeout)

    def solve_all(
        self, grid: Grid, timeout: float = 60.0
    ) -> dict[SolverType, SolveResult]:
        """Solve a puzzle using all registered solvers.

        Runs each registered solver on the same puzzle and collects results.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed per solver. Defaults to 60.0.

        Returns:
            Dictionary mapping each SolverType to its SolveResult.
        """
        results: dict[SolverType, SolveResult] = {}
        for solver_type, solver in self._solvers.items():
            results[solver_type] = solver.solve(grid, timeout=timeout)
        return results

    def solve_stepwise(
        self, grid: Grid, solver_type: SolverType, timeout: float = 60.0
    ) -> Generator[StepEvent, None, SolveResult]:
        """Solve a puzzle step-by-step using the specified solver.

        Routes the stepwise solve request to the appropriate solver,
        yielding StepEvents for each state transition during solving.

        Args:
            grid: The initial puzzle grid (not mutated).
            solver_type: Which solver algorithm to use.
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Yields:
            StepEvent for each state transition (assignment, backtrack, swap).

        Returns:
            SolveResult upon completion.

        Raises:
            ValueError: If no solver is registered for the given solver_type.
        """
        solver = self._get_solver(solver_type)
        return solver.solve_stepwise(grid, timeout=timeout)

    def _get_solver(self, solver_type: SolverType) -> SolverProtocol:
        """Retrieve the solver for the given type.

        Args:
            solver_type: The SolverType to look up.

        Returns:
            The registered SolverProtocol instance.

        Raises:
            ValueError: If no solver is registered for the given solver_type.
        """
        if solver_type not in self._solvers:
            raise ValueError(
                f"No solver registered for type '{solver_type.value}'. "
                f"Available types: {[t.value for t in self._solvers]}"
            )
        return self._solvers[solver_type]

    @property
    def registered_solvers(self) -> dict[SolverType, SolverProtocol]:
        """Get all registered solvers.

        Returns:
            Dictionary mapping SolverType to SolverProtocol instances.
        """
        return dict(self._solvers)


__all__ = [
    "BacktrackingSolver",
    "ForwardCheckingSolver",
    "InformedSolver",
    "SimulatedAnnealingSolver",
    "SolverManager",
]
