"""Abstract base classes and protocols for the Sudoku Solver and Evaluator system.

Defines the interfaces that all solvers, generators, and evaluators must implement.
This enables modularity and testability by allowing modules to depend on interfaces
rather than concrete implementations (Requirement 11.2, 11.7).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from sudoku_solver_evaluator.models.enums import DifficultyLevel
    from sudoku_solver_evaluator.models.grid import Grid
    from sudoku_solver_evaluator.models.metrics import (
        AggregateStats,
        ComparisonTable,
        SolveResult,
        StepEvent,
    )


class SolverProtocol(ABC):
    """Base interface for all Sudoku solvers.

    All solver implementations must inherit from this class and provide
    concrete implementations of solve, solve_stepwise, and the name property.
    This ensures a uniform interface for the SolverManager and UI components.
    """

    @abstractmethod
    def solve(self, grid: Grid, timeout: float = 60.0) -> SolveResult:
        """Solve the given puzzle within the timeout.

        The solver must work on a copy of the input grid and never mutate
        the original. If the puzzle is unsolvable or the timeout is exceeded,
        an appropriate SolveResult status is returned.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Returns:
            SolveResult containing the solution (if found), metrics, and status.
        """
        ...

    @abstractmethod
    def solve_stepwise(
        self, grid: Grid, timeout: float = 60.0
    ) -> Generator[StepEvent, None, SolveResult]:
        """Solve the puzzle yielding StepEvents for visualization.

        Each state transition (assignment, backtrack, swap, propagation) is
        emitted as a StepEvent, enabling the UI to display step-by-step
        progress. The final SolveResult is returned when the generator
        completes.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Yields:
            StepEvent for each state transition (assignment, backtrack, swap).

        Returns:
            SolveResult upon completion.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the solver.

        Returns:
            A string identifying this solver (e.g., 'Backtracking Search').
        """
        ...


class PuzzleGeneratorProtocol(ABC):
    """Interface for puzzle generation.

    Implementations produce valid Sudoku puzzles with exactly one solution
    at the requested difficulty level.
    """

    @abstractmethod
    def generate(self, difficulty: DifficultyLevel, timeout: float = 30.0) -> Grid:
        """Generate a valid Sudoku puzzle with exactly one solution.

        Creates a complete valid grid using backtracking with random value
        ordering, then removes cells based on the difficulty level to produce
        a puzzle. The puzzle is verified to have exactly one solution before
        being returned.

        Args:
            difficulty: The target difficulty level determining how many
                cells are pre-filled.
            timeout: Maximum generation time in seconds. Defaults to 30.0.

        Returns:
            A Grid with pre-filled cells appropriate for the difficulty.

        Raises:
            TimeoutError: If generation exceeds the timeout.
            ValueError: If difficulty is not a valid DifficultyLevel.
        """
        ...


class PerformanceEvaluatorProtocol(ABC):
    """Interface for performance recording and analysis.

    Implementations record solve results and compute statistics for
    comparing algorithm performance across puzzles and difficulty levels.
    """

    @abstractmethod
    def record(
        self, result: SolveResult, puzzle_id: str, difficulty: DifficultyLevel
    ) -> None:
        """Record a solve result for later analysis.

        Stores the result keyed by puzzle_id and difficulty for use in
        comparisons and aggregate statistics.

        Args:
            result: The SolveResult from a solver run.
            puzzle_id: Unique identifier for the puzzle that was solved.
            difficulty: The difficulty level of the puzzle.
        """
        ...

    @abstractmethod
    def get_comparison(self, puzzle_id: str) -> ComparisonTable:
        """Get comparison data for all algorithms on a given puzzle.

        Returns a table comparing time, states explored, backtracks, and
        optimality rankings for all solvers that have recorded results
        for the specified puzzle.

        Args:
            puzzle_id: The unique identifier of the puzzle to compare.

        Returns:
            ComparisonTable with results and rankings for the puzzle.
        """
        ...

    @abstractmethod
    def get_aggregate(self, difficulty: DifficultyLevel) -> AggregateStats:
        """Get aggregate statistics for a difficulty level.

        Computes mean, min, and max for each metric across all puzzles
        of the specified difficulty level. Requires a minimum of 5 puzzles
        for meaningful statistics.

        Args:
            difficulty: The difficulty level to aggregate over.

        Returns:
            AggregateStats with per-algorithm statistics.
        """
        ...

    @abstractmethod
    def export_csv(self, filepath: str) -> None:
        """Export all recorded results to CSV.

        Writes a CSV file with columns: puzzle_id, difficulty_level,
        algorithm_name, time_taken, states_explored, backtracks,
        optimality_rank.

        Args:
            filepath: The file path where the CSV will be written.

        Raises:
            OSError: If the file cannot be written.
        """
        ...
