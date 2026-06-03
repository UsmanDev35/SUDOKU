"""Backtracking Search solver (uninformed depth-first search).

This module implements a classic backtracking solver for Sudoku puzzles.
The algorithm performs exhaustive depth-first search through the solution
space without any domain heuristics or constraint propagation.

Algorithm Overview:
    1. Validate the initial grid for pre-existing constraint violations.
    2. Identify all empty cells in left-to-right, top-to-bottom order.
    3. For each empty cell, try values 1-9 in ascending order.
    4. After each assignment, check row/column/box constraints.
    5. If a constraint is violated, undo the assignment (backtrack) and
       try the next value.
    6. If all values are exhausted, backtrack to the previous cell.
    7. If all cells are filled without violations, the puzzle is solved.

This is the simplest solver strategy and serves as a baseline for
comparing against informed and heuristic-based approaches.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
"""

import time
from typing import Generator, Optional

from sudoku_solver_evaluator.constraints.validator import is_grid_valid, is_valid_assignment
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol


class BacktrackingSolver(SolverProtocol):
    """Backtracking Search solver using uninformed depth-first search.

    This solver explores the search space by assigning values to cells in a
    fixed left-to-right, top-to-bottom order. For each cell, values 1-9 are
    tried sequentially. When a constraint violation is detected, the solver
    backtracks and tries the next value.

    The solver is deterministic: given the same puzzle, it will always explore
    the same sequence of states and produce the same result.

    Attributes:
        _name: Human-readable name identifying this solver.
    """

    def __init__(self) -> None:
        """Initialize the BacktrackingSolver."""
        self._name = "Backtracking Search"

    @property
    def name(self) -> str:
        """Human-readable name of the solver.

        Returns:
            The string 'Backtracking Search'.
        """
        return self._name

    def solve(self, grid: Grid, timeout: float = 60.0) -> SolveResult:
        """Solve the given Sudoku puzzle using backtracking search.

        Works on a deep copy of the input grid to avoid mutating the original.
        Validates the initial grid for constraint violations before starting
        the search. If the grid is invalid, returns UNSOLVABLE immediately.

        The algorithm uses an iterative approach with an explicit stack to
        avoid Python recursion limits on deeply nested puzzles.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Returns:
            SolveResult containing:
                - SOLVED status with the completed grid if a solution is found.
                - UNSOLVABLE status if no solution exists or the grid is invalid.
                - TIMEOUT status with partial metrics if the timeout is exceeded.
        """
        # Record the start time using monotonic clock to avoid system clock drift
        start_time = time.monotonic()

        # Work on a copy of the grid to never mutate the original (Requirement 2.8)
        working_grid = grid.copy()

        # Validate initial grid: check for pre-existing constraint violations
        # If the grid already has conflicts, it's unsolvable (Requirement 2.8)
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Get all empty cells in left-to-right, top-to-bottom order (Requirement 2.1)
        # This ordering is: row 0 col 0, row 0 col 1, ..., row 8 col 8
        # The Grid.get_empty_cells() already iterates row-by-row, col-by-col
        empty_cells = working_grid.get_empty_cells()

        # If there are no empty cells, the grid is already complete
        if not empty_cells:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Metrics counters
        states_explored = 0
        backtracks = 0

        # Iterative backtracking using an index into the empty_cells list
        # cell_index tracks which empty cell we're currently trying to fill
        cell_index = 0

        # Track the last value tried for each cell position to enable backtracking
        # When we backtrack to a cell, we continue from the next value after
        # the one that was previously assigned
        last_tried: list[int] = [0] * len(empty_cells)  # 0 means no value tried yet

        while 0 <= cell_index < len(empty_cells):
            # Check timeout using monotonic clock (Requirement: configurable timeout)
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.BACKTRACKING,
                    status=SolveStatus.TIMEOUT,
                    solved_grid=None,
                    time_ms=elapsed_ms,
                    states_explored=states_explored,
                    backtracks=backtracks,
                )

            cell = empty_cells[cell_index]
            row, col = cell.row, cell.col

            # Start trying values from where we left off (or from 1 if fresh)
            start_value = last_tried[cell_index] + 1
            found_valid = False

            # Try values in ascending order: 1, 2, 3, ..., 9 (Requirement 2.2)
            for value in range(start_value, 10):
                # Check if this value satisfies all constraints (Requirement 2.3)
                if is_valid_assignment(working_grid, row, col, value):
                    # Valid assignment found - place the value
                    working_grid.set_value(row, col, value)
                    last_tried[cell_index] = value

                    # Increment states_explored for each assignment (Requirement 2.7)
                    states_explored += 1

                    # Move to the next empty cell
                    cell_index += 1
                    found_valid = True
                    break

            if not found_valid:
                # All values 1-9 exhausted for this cell without finding a valid
                # assignment. We must backtrack to the previous cell (Requirement 2.4).

                # Clear the current cell and reset its tracking
                working_grid.clear_value(row, col)
                last_tried[cell_index] = 0

                # Move back to the previous empty cell
                cell_index -= 1

                # Increment backtracks counter (Requirement 2.7)
                backtracks += 1

                # If we backtracked past the first empty cell, puzzle is unsolvable
                if cell_index >= 0:
                    # Clear the value at the cell we're backtracking to
                    # so we can try the next value for it
                    prev_cell = empty_cells[cell_index]
                    working_grid.clear_value(prev_cell.row, prev_cell.col)

        # Determine the result based on where cell_index ended up
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if cell_index == len(empty_cells):
            # Successfully filled all empty cells (Requirement 2.5)
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=states_explored,
                backtracks=backtracks,
            )
        else:
            # Backtracked past the first cell - no solution exists (Requirement 2.6)
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored,
                backtracks=backtracks,
            )

    def solve_stepwise(
        self, grid: Grid, timeout: float = 60.0
    ) -> Generator[StepEvent, None, SolveResult]:
        """Solve the puzzle yielding StepEvents for each state transition.

        This method implements the same backtracking algorithm as solve() but
        yields a StepEvent for each assignment (ASSIGN) and each backtrack
        (BACKTRACK) operation. This enables the UI to display step-by-step
        progress of the solving process.

        The StepEvent includes running metrics (states_explored, backtracks)
        at the time of the event, allowing real-time metric display.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Yields:
            StepEvent with step_type ASSIGN when a value is placed in a cell.
            StepEvent with step_type BACKTRACK when a value is removed from a cell.

        Returns:
            SolveResult upon completion (same semantics as solve()).
        """
        # Record the start time using monotonic clock
        start_time = time.monotonic()

        # Work on a copy of the grid to never mutate the original
        working_grid = grid.copy()

        # Validate initial grid for pre-existing constraint violations
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Get empty cells in left-to-right, top-to-bottom order
        empty_cells = working_grid.get_empty_cells()

        # If no empty cells, puzzle is already complete
        if not empty_cells:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Metrics counters
        states_explored = 0
        backtracks = 0

        # Iterative backtracking with explicit stack
        cell_index = 0
        last_tried: list[int] = [0] * len(empty_cells)

        while 0 <= cell_index < len(empty_cells):
            # Check timeout
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.BACKTRACKING,
                    status=SolveStatus.TIMEOUT,
                    solved_grid=None,
                    time_ms=elapsed_ms,
                    states_explored=states_explored,
                    backtracks=backtracks,
                )

            cell = empty_cells[cell_index]
            row, col = cell.row, cell.col

            start_value = last_tried[cell_index] + 1
            found_valid = False

            # Try values 1-9 in ascending order
            for value in range(start_value, 10):
                if is_valid_assignment(working_grid, row, col, value):
                    # Place the value
                    working_grid.set_value(row, col, value)
                    last_tried[cell_index] = value
                    states_explored += 1

                    # Emit ASSIGN step event before moving to next cell
                    yield StepEvent(
                        step_type=StepType.ASSIGN,
                        row=row,
                        col=col,
                        value=value,
                        previous_value=None,
                        states_explored=states_explored,
                        backtracks=backtracks,
                    )

                    # Move to next cell
                    cell_index += 1
                    found_valid = True
                    break

            if not found_valid:
                # All values exhausted - must backtrack
                working_grid.clear_value(row, col)
                last_tried[cell_index] = 0

                # Move back to previous cell
                cell_index -= 1
                backtracks += 1

                if cell_index >= 0:
                    # Get the previous cell's current value before clearing
                    prev_cell = empty_cells[cell_index]
                    previous_value = working_grid.get_cell(prev_cell.row, prev_cell.col).value

                    # Clear the previous cell so we can try next value
                    working_grid.clear_value(prev_cell.row, prev_cell.col)

                    # Emit BACKTRACK step event
                    yield StepEvent(
                        step_type=StepType.BACKTRACK,
                        row=prev_cell.row,
                        col=prev_cell.col,
                        value=None,
                        previous_value=previous_value,
                        states_explored=states_explored,
                        backtracks=backtracks,
                    )

        # Determine result
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if cell_index == len(empty_cells):
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=states_explored,
                backtracks=backtracks,
            )
        else:
            return SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored,
                backtracks=backtracks,
            )
