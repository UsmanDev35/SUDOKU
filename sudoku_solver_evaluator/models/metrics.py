"""Metrics and result dataclasses for the Sudoku Solver and Evaluator system.

Contains data structures for solve results, step events, comparison tables,
aggregate statistics, and adversarial race results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from sudoku_solver_evaluator.models.enums import (
    DifficultyLevel,
    SolveStatus,
    SolverType,
    StepType,
)

if TYPE_CHECKING:
    from sudoku_solver_evaluator.models.grid import Grid


@dataclass
class SolveResult:
    """Result of a solve operation.

    Attributes:
        solver_type: The algorithm that produced this result.
        status: Outcome of the solve attempt.
        solved_grid: The completed grid if solved, None otherwise.
        time_ms: Wall-clock time in milliseconds.
        states_explored: Number of states explored (assignments made).
        backtracks: Number of backtracks performed (for backtracking-based solvers).
        restarts: Number of restarts performed (for SA solver).
        best_cost: Lowest cost encountered (for SA solver).
    """

    solver_type: SolverType
    status: SolveStatus
    solved_grid: Optional["Grid"] = None
    time_ms: int = 0
    states_explored: int = 0
    backtracks: int = 0
    restarts: int = 0
    best_cost: Optional[int] = None


@dataclass
class StepEvent:
    """A single step in the solving process for visualization.

    Attributes:
        step_type: The type of step (assign, backtrack, swap, propagate).
        row: Row index of the primary cell involved (0-8).
        col: Column index of the primary cell involved (0-8).
        value: The value being assigned or involved in the step.
        previous_value: The value that was in the cell before this step.
        swap_row: Row index of the second cell in a swap (SA only).
        swap_col: Column index of the second cell in a swap (SA only).
        states_explored: Running count of states explored at this step.
        backtracks: Running count of backtracks at this step.
        current_cost: Current cost value (SA only).
    """

    step_type: StepType
    row: int
    col: int
    value: Optional[int] = None
    previous_value: Optional[int] = None
    swap_row: Optional[int] = None
    swap_col: Optional[int] = None
    states_explored: int = 0
    backtracks: int = 0
    current_cost: Optional[int] = None


@dataclass
class ComparisonTable:
    """Comparison data for all algorithms on a single puzzle.

    Attributes:
        puzzle_id: Unique identifier for the puzzle.
        difficulty: The difficulty level of the puzzle.
        results: Mapping of solver type to its solve result.
        rankings: Mapping of metric name to solvers ranked by that metric.
    """

    puzzle_id: str
    difficulty: DifficultyLevel
    results: dict[SolverType, SolveResult] = field(default_factory=dict)
    rankings: dict[str, list[SolverType]] = field(default_factory=dict)


@dataclass
class AlgorithmStats:
    """Mean/min/max statistics for a single algorithm across multiple puzzles.

    Attributes:
        mean_time_ms: Average solve time in milliseconds.
        min_time_ms: Minimum solve time in milliseconds.
        max_time_ms: Maximum solve time in milliseconds.
        mean_states: Average number of states explored.
        min_states: Minimum number of states explored.
        max_states: Maximum number of states explored.
        mean_backtracks: Average number of backtracks.
        min_backtracks: Minimum number of backtracks.
        max_backtracks: Maximum number of backtracks.
        solve_rate: Fraction of puzzles solved successfully (0.0 to 1.0).
    """

    mean_time_ms: float
    min_time_ms: int
    max_time_ms: int
    mean_states: float
    min_states: int
    max_states: int
    mean_backtracks: float
    min_backtracks: int
    max_backtracks: int
    solve_rate: float


@dataclass
class AggregateStats:
    """Aggregate statistics for a difficulty level across multiple puzzles.

    Attributes:
        difficulty: The difficulty level these stats apply to.
        puzzle_count: Number of puzzles included in the aggregation.
        stats: Mapping of solver type to its aggregate statistics.
    """

    difficulty: DifficultyLevel
    puzzle_count: int
    stats: dict[SolverType, AlgorithmStats] = field(default_factory=dict)


@dataclass
class RaceResult:
    """Result of an adversarial race between two solvers.

    Attributes:
        solver_a_type: The first solver in the race.
        solver_b_type: The second solver in the race.
        solver_a_result: Solve result for the first solver.
        solver_b_result: Solve result for the second solver.
        winner: The solver that won, or None if tie.
        time_difference_ms: Time difference between the two solvers in milliseconds.
    """

    solver_a_type: SolverType
    solver_b_type: SolverType
    solver_a_result: SolveResult
    solver_b_result: SolveResult
    winner: Optional[SolverType]
    time_difference_ms: int


@dataclass
class RaceStatus:
    """Live status of a solver during an adversarial race.

    Attributes:
        solver_type: The solver being tracked.
        states_explored: Number of states explored so far.
        elapsed_ms: Elapsed time in milliseconds.
        is_complete: Whether the solver has finished.
    """

    solver_type: SolverType
    states_explored: int
    elapsed_ms: int
    is_complete: bool
