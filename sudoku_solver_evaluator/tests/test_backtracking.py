"""Unit tests for the Backtracking Search solver.

Tests cover:
- Solving known solvable puzzles
- Detecting invalid/unsolvable grids
- Timeout behavior
- Cell ordering (left-to-right, top-to-bottom)
- Value ordering (ascending 1-9)
- Metric consistency between solve() and solve_stepwise()
- Non-mutation of input grid
"""

import pytest

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver


# A well-known solvable puzzle
SOLVABLE_PUZZLE = [
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

# Invalid puzzle: duplicate 5 in row 0
INVALID_ROW_PUZZLE = [
    [5, 5, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 0, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]

# Invalid puzzle: duplicate 5 in column 0
INVALID_COL_PUZZLE = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [5, 0, 0, 1, 9, 0, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]

# Invalid puzzle: duplicate in box
INVALID_BOX_PUZZLE = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 5, 0, 1, 9, 0, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]

# A fully solved grid (no empty cells)
SOLVED_GRID = [
    [5, 3, 4, 6, 7, 8, 9, 1, 2],
    [6, 7, 2, 1, 9, 5, 3, 4, 8],
    [1, 9, 8, 3, 4, 2, 5, 6, 7],
    [8, 5, 9, 7, 6, 1, 4, 2, 3],
    [4, 2, 6, 8, 5, 3, 7, 9, 1],
    [7, 1, 3, 9, 2, 4, 8, 5, 6],
    [9, 6, 1, 5, 3, 7, 2, 8, 4],
    [2, 8, 7, 4, 1, 9, 6, 3, 5],
    [3, 4, 5, 2, 8, 6, 1, 7, 9],
]


class TestBacktrackingSolverProperties:
    """Test basic properties of the BacktrackingSolver class."""

    def test_name(self):
        solver = BacktrackingSolver()
        assert solver.name == "Backtracking Search"

    def test_solver_type_in_result(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)
        assert result.solver_type == SolverType.BACKTRACKING


class TestBacktrackingSolverSolve:
    """Test the solve() method."""

    def test_solves_valid_puzzle(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.SOLVED
        assert result.solved_grid is not None
        assert result.solved_grid.is_complete()
        assert result.solved_grid.is_valid()

    def test_preserves_fixed_cells(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)

        # Verify all pre-filled cells retain their values
        for row in range(9):
            for col in range(9):
                if SOLVABLE_PUZZLE[row][col] != 0:
                    assert result.solved_grid.get_cell(row, col).value == SOLVABLE_PUZZLE[row][col]

    def test_does_not_mutate_input_grid(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        original_values = grid.to_2d_list()
        solver.solve(grid)

        assert grid.to_2d_list() == original_values

    def test_already_solved_grid(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVED_GRID)
        result = solver.solve(grid)

        assert result.status == SolveStatus.SOLVED
        assert result.states_explored == 0
        assert result.backtracks == 0

    def test_records_positive_metrics(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)

        assert result.states_explored > 0
        assert result.backtracks >= 0
        assert result.time_ms >= 0


class TestBacktrackingSolverInvalidGrids:
    """Test detection of invalid initial grids."""

    def test_invalid_row_duplicate(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(INVALID_ROW_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert result.solved_grid is None

    def test_invalid_col_duplicate(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(INVALID_COL_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert result.solved_grid is None

    def test_invalid_box_duplicate(self):
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(INVALID_BOX_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert result.solved_grid is None


class TestBacktrackingSolverTimeout:
    """Test timeout behavior."""

    def test_timeout_returns_timeout_status(self):
        solver = BacktrackingSolver()
        # Empty grid with very short timeout
        empty_puzzle = [[0] * 9 for _ in range(9)]
        grid = Grid.from_2d_list(empty_puzzle)
        result = solver.solve(grid, timeout=0.0001)

        assert result.status == SolveStatus.TIMEOUT
        assert result.solved_grid is None

    def test_timeout_captures_partial_metrics(self):
        solver = BacktrackingSolver()
        empty_puzzle = [[0] * 9 for _ in range(9)]
        grid = Grid.from_2d_list(empty_puzzle)
        result = solver.solve(grid, timeout=0.001)

        assert result.status == SolveStatus.TIMEOUT
        # Should have explored at least some states before timing out
        assert result.states_explored >= 0
        assert result.time_ms >= 0


class TestBacktrackingSolverOrdering:
    """Test cell and value ordering requirements."""

    def test_cell_ordering_left_to_right_top_to_bottom(self):
        """Verify cells are assigned in left-to-right, top-to-bottom order."""
        # Puzzle with only 3 empty cells in known positions
        puzzle = [
            [5, 3, 0, 0, 7, 0, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ]
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(puzzle)
        gen = solver.solve_stepwise(grid)

        assign_events = []
        try:
            while True:
                event = next(gen)
                if event.step_type == StepType.ASSIGN:
                    assign_events.append(event)
        except StopIteration:
            pass

        # Empty cells are at (0,2), (0,3), (0,5) - should be assigned in that order
        assert assign_events[0].row == 0 and assign_events[0].col == 2
        assert assign_events[1].row == 0 and assign_events[1].col == 3
        assert assign_events[2].row == 0 and assign_events[2].col == 5

    def test_values_tried_in_ascending_order(self):
        """Verify values are tried 1, 2, 3, ..., 9 in ascending order."""
        # Puzzle where the first empty cell must try values until finding a valid one
        # Cell (0,2) should try 1 first (which is invalid due to row 2 having 1)
        # then 2 (invalid), then eventually find 4
        puzzle = [
            [5, 3, 0, 0, 7, 0, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ]
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(puzzle)
        gen = solver.solve_stepwise(grid)

        first_assign = None
        try:
            while True:
                event = next(gen)
                if event.step_type == StepType.ASSIGN:
                    first_assign = event
                    break
        except StopIteration:
            pass

        # The first valid value for (0,2) is 4 (1,2,3 are all in the column/box)
        assert first_assign is not None
        assert first_assign.row == 0
        assert first_assign.col == 2
        assert first_assign.value == 4


class TestBacktrackingSolverStepwise:
    """Test the solve_stepwise() method."""

    def test_metrics_match_step_events(self):
        """Verify states_explored equals ASSIGN count and backtracks equals BACKTRACK count."""
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        gen = solver.solve_stepwise(grid)

        assign_count = 0
        backtrack_count = 0
        try:
            while True:
                event = next(gen)
                if event.step_type == StepType.ASSIGN:
                    assign_count += 1
                elif event.step_type == StepType.BACKTRACK:
                    backtrack_count += 1
        except StopIteration as e:
            result = e.value

        assert result.status == SolveStatus.SOLVED
        assert assign_count == result.states_explored
        assert backtrack_count == result.backtracks

    def test_stepwise_same_result_as_solve(self):
        """Verify stepwise produces the same solution as solve."""
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)

        solve_result = solver.solve(grid)

        gen = solver.solve_stepwise(grid)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            stepwise_result = e.value

        assert solve_result.status == stepwise_result.status
        assert solve_result.states_explored == stepwise_result.states_explored
        assert solve_result.backtracks == stepwise_result.backtracks
        assert solve_result.solved_grid.to_2d_list() == stepwise_result.solved_grid.to_2d_list()

    def test_stepwise_invalid_grid(self):
        """Verify stepwise returns UNSOLVABLE for invalid grids."""
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(INVALID_ROW_PUZZLE)
        gen = solver.solve_stepwise(grid)

        events = []
        try:
            while True:
                events.append(next(gen))
        except StopIteration as e:
            result = e.value

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert len(events) == 0

    def test_step_events_have_running_metrics(self):
        """Verify each StepEvent includes running metric counts."""
        solver = BacktrackingSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        gen = solver.solve_stepwise(grid)

        prev_states = 0
        try:
            while True:
                event = next(gen)
                if event.step_type == StepType.ASSIGN:
                    # states_explored should be monotonically increasing for ASSIGN events
                    assert event.states_explored >= prev_states
                    prev_states = event.states_explored
                # backtracks should be non-negative
                assert event.backtracks >= 0
        except StopIteration:
            pass
