"""Unit tests for the SolverManager facade.

Tests registration, routing, solve, solve_all, and solve_stepwise methods.
"""

import pytest

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers import (
    BacktrackingSolver,
    ForwardCheckingSolver,
    InformedSolver,
    SimulatedAnnealingSolver,
    SolverManager,
)


# A simple puzzle with a known solution for testing
SIMPLE_PUZZLE = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]


@pytest.fixture
def manager() -> SolverManager:
    """Create a SolverManager with default registrations."""
    return SolverManager()


@pytest.fixture
def grid() -> Grid:
    """Create a simple puzzle grid."""
    return Grid.from_2d_list(SIMPLE_PUZZLE)


class TestSolverManagerInit:
    """Tests for SolverManager initialization."""

    def test_registers_all_four_solvers(self, manager: SolverManager) -> None:
        """All four solver types should be registered on initialization."""
        registered = manager.registered_solvers
        assert SolverType.BACKTRACKING in registered
        assert SolverType.INFORMED in registered
        assert SolverType.LOCAL_SEARCH in registered
        assert SolverType.FORWARD_CHECKING in registered

    def test_backtracking_solver_type(self, manager: SolverManager) -> None:
        """Backtracking type maps to BacktrackingSolver instance."""
        assert isinstance(manager.registered_solvers[SolverType.BACKTRACKING], BacktrackingSolver)

    def test_informed_solver_type(self, manager: SolverManager) -> None:
        """Informed type maps to InformedSolver instance."""
        assert isinstance(manager.registered_solvers[SolverType.INFORMED], InformedSolver)

    def test_local_search_solver_type(self, manager: SolverManager) -> None:
        """Local search type maps to SimulatedAnnealingSolver instance."""
        assert isinstance(manager.registered_solvers[SolverType.LOCAL_SEARCH], SimulatedAnnealingSolver)

    def test_forward_checking_solver_type(self, manager: SolverManager) -> None:
        """Forward checking type maps to ForwardCheckingSolver instance."""
        assert isinstance(manager.registered_solvers[SolverType.FORWARD_CHECKING], ForwardCheckingSolver)


class TestSolverManagerRegister:
    """Tests for the register method."""

    def test_register_replaces_existing(self, manager: SolverManager) -> None:
        """Registering a solver for an existing type replaces it."""
        new_solver = BacktrackingSolver()
        manager.register(SolverType.BACKTRACKING, new_solver)
        assert manager.registered_solvers[SolverType.BACKTRACKING] is new_solver

    def test_register_invalid_type_raises(self, manager: SolverManager) -> None:
        """Registering a non-SolverProtocol raises TypeError."""
        with pytest.raises(TypeError):
            manager.register(SolverType.BACKTRACKING, "not a solver")  # type: ignore


class TestSolverManagerSolve:
    """Tests for the solve method."""

    def test_solve_backtracking(self, manager: SolverManager, grid: Grid) -> None:
        """Solve with backtracking returns a solved result."""
        result = manager.solve(grid, SolverType.BACKTRACKING)
        assert result.status == SolveStatus.SOLVED
        assert result.solver_type == SolverType.BACKTRACKING
        assert result.solved_grid is not None

    def test_solve_informed(self, manager: SolverManager, grid: Grid) -> None:
        """Solve with informed solver returns a solved result."""
        result = manager.solve(grid, SolverType.INFORMED)
        assert result.status == SolveStatus.SOLVED
        assert result.solver_type == SolverType.INFORMED

    def test_solve_forward_checking(self, manager: SolverManager, grid: Grid) -> None:
        """Solve with forward checking returns a solved result."""
        result = manager.solve(grid, SolverType.FORWARD_CHECKING)
        assert result.status == SolveStatus.SOLVED
        assert result.solver_type == SolverType.FORWARD_CHECKING

    def test_solve_unregistered_type_raises(self, manager: SolverManager, grid: Grid) -> None:
        """Solving with an unregistered solver type raises ValueError."""
        # Remove a solver to test
        del manager._solvers[SolverType.BACKTRACKING]
        with pytest.raises(ValueError, match="No solver registered"):
            manager.solve(grid, SolverType.BACKTRACKING)

    def test_solve_does_not_mutate_original_grid(self, manager: SolverManager, grid: Grid) -> None:
        """The original grid should not be mutated by solving."""
        original_values = grid.to_2d_list()
        manager.solve(grid, SolverType.BACKTRACKING)
        assert grid.to_2d_list() == original_values


class TestSolverManagerSolveAll:
    """Tests for the solve_all method."""

    def test_solve_all_returns_all_types(self, manager: SolverManager, grid: Grid) -> None:
        """solve_all returns results for all registered solver types."""
        results = manager.solve_all(grid, timeout=60.0)
        assert SolverType.BACKTRACKING in results
        assert SolverType.INFORMED in results
        assert SolverType.LOCAL_SEARCH in results
        assert SolverType.FORWARD_CHECKING in results

    def test_solve_all_deterministic_solvers_produce_valid_solutions(
        self, manager: SolverManager, grid: Grid
    ) -> None:
        """Deterministic solvers (backtracking, informed, FC) should all solve."""
        results = manager.solve_all(grid, timeout=60.0)
        for solver_type in [SolverType.BACKTRACKING, SolverType.INFORMED, SolverType.FORWARD_CHECKING]:
            assert results[solver_type].status == SolveStatus.SOLVED
            assert results[solver_type].solved_grid is not None


class TestSolverManagerSolveStepwise:
    """Tests for the solve_stepwise method."""

    def test_solve_stepwise_returns_generator(self, manager: SolverManager, grid: Grid) -> None:
        """solve_stepwise returns a generator that yields StepEvents."""
        gen = manager.solve_stepwise(grid, SolverType.BACKTRACKING)
        # Consume the generator
        steps = []
        try:
            while True:
                step = next(gen)
                steps.append(step)
        except StopIteration as e:
            result = e.value

        assert len(steps) > 0
        assert result.status == SolveStatus.SOLVED

    def test_solve_stepwise_unregistered_raises(self, manager: SolverManager, grid: Grid) -> None:
        """solve_stepwise with unregistered type raises ValueError."""
        del manager._solvers[SolverType.INFORMED]
        with pytest.raises(ValueError, match="No solver registered"):
            manager.solve_stepwise(grid, SolverType.INFORMED)
