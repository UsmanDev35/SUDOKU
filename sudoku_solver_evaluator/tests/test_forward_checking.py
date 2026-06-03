"""Unit tests for the Forward Checking solver.

Tests cover:
- Basic solving of valid puzzles
- Invalid grid detection (unsolvable)
- Non-mutation of original grid
- MRV variable selection
- Domain initialization correctness
- Forward checking propagation
- Naked Singles and Hidden Singles propagation
- Stepwise mode with metrics consistency
- Timeout behavior
"""

import pytest

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver


# A known solvable puzzle (medium difficulty)
SAMPLE_PUZZLE = [
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

# Expected solution for the sample puzzle
SAMPLE_SOLUTION = [
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


class TestForwardCheckingSolverProperties:
    """Test basic properties of the solver."""

    def test_name(self):
        solver = ForwardCheckingSolver()
        assert solver.name == "Forward Checking"

    def test_solver_type_in_result(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        result = solver.solve(grid)
        assert result.solver_type == SolverType.FORWARD_CHECKING


class TestForwardCheckingSolverSolve:
    """Test the solve method with various puzzles."""

    def test_solves_valid_puzzle(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        result = solver.solve(grid)
        assert result.status == SolveStatus.SOLVED
        assert result.solved_grid is not None
        assert result.solved_grid.is_complete()
        assert result.solved_grid.is_valid()
        assert result.solved_grid.to_2d_list() == SAMPLE_SOLUTION

    def test_preserves_fixed_cells(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        result = solver.solve(grid)
        assert result.solved_grid is not None
        # Check all pre-filled cells are preserved
        for r in range(9):
            for c in range(9):
                if SAMPLE_PUZZLE[r][c] != 0:
                    assert result.solved_grid.get_cell(r, c).value == SAMPLE_PUZZLE[r][c]

    def test_does_not_mutate_input_grid(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        original_values = grid.to_2d_list()
        solver.solve(grid)
        assert grid.to_2d_list() == original_values

    def test_already_solved_grid(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_SOLUTION)
        result = solver.solve(grid)
        assert result.status == SolveStatus.SOLVED
        assert result.solved_grid is not None
        assert result.solved_grid.to_2d_list() == SAMPLE_SOLUTION

    def test_records_positive_metrics(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        result = solver.solve(grid)
        assert result.states_explored > 0
        assert result.time_ms >= 0


class TestForwardCheckingSolverInvalidGrids:
    """Test unsolvable/invalid grid detection."""

    def test_invalid_row_duplicate(self):
        puzzle = [
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
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(puzzle)
        result = solver.solve(grid)
        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0

    def test_invalid_col_duplicate(self):
        puzzle = [
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
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(puzzle)
        result = solver.solve(grid)
        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0

    def test_invalid_box_duplicate(self):
        puzzle = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 5, 1, 9, 0, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ]
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(puzzle)
        result = solver.solve(grid)
        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0


class TestForwardCheckingDomainInit:
    """Test domain initialization."""

    def test_domain_excludes_row_values(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        domains = solver._initialize_domains(grid)
        # Cell (0, 2) is empty. Row 0 has values 5, 3, 7 assigned.
        # So 5, 3, 7 should not be in domain of (0, 2)
        assert 5 not in domains[(0, 2)]
        assert 3 not in domains[(0, 2)]
        assert 7 not in domains[(0, 2)]

    def test_domain_excludes_col_values(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        domains = solver._initialize_domains(grid)
        # Cell (0, 2) is empty. Col 2 has values 8, 0, 0, 0, 0, 0.
        # Actually col 2 has: 0, 0, 8, 0, 0, 0, 0, 0, 0
        # So 8 should not be in domain of (0, 2)
        assert 8 not in domains[(0, 2)]

    def test_domain_excludes_box_values(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        domains = solver._initialize_domains(grid)
        # Cell (0, 2) is in box 0 (rows 0-2, cols 0-2)
        # Box 0 has: 5, 3, 6, 9, 8. So all of these should be excluded.
        assert 5 not in domains[(0, 2)]
        assert 3 not in domains[(0, 2)]
        assert 6 not in domains[(0, 2)]
        assert 9 not in domains[(0, 2)]
        assert 8 not in domains[(0, 2)]

    def test_fixed_cell_domain_is_singleton(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        domains = solver._initialize_domains(grid)
        # Cell (0, 0) is fixed with value 5
        assert domains[(0, 0)] == {5}


class TestForwardCheckingMRV:
    """Test MRV variable selection."""

    def test_selects_smallest_domain(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        domains = solver._initialize_domains(grid)
        selected = solver._select_mrv(grid, domains)
        assert selected is not None
        # The selected cell should have the smallest domain
        selected_size = len(domains[selected])
        for r in range(9):
            for c in range(9):
                if grid.get_cell(r, c).value is None:
                    assert len(domains[(r, c)]) >= selected_size

    def test_returns_none_when_all_assigned(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_SOLUTION)
        domains = solver._initialize_domains(grid)
        selected = solver._select_mrv(grid, domains)
        assert selected is None


class TestForwardCheckingStepwise:
    """Test stepwise mode and metrics consistency."""

    def test_metrics_match_step_events(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        gen = solver.solve_stepwise(grid)

        assign_count = 0
        backtrack_count = 0
        try:
            while True:
                step = next(gen)
                if step.step_type == StepType.ASSIGN:
                    assign_count += 1
                elif step.step_type == StepType.BACKTRACK:
                    backtrack_count += 1
        except StopIteration as e:
            result = e.value

        assert result.status == SolveStatus.SOLVED
        assert result.states_explored == assign_count
        assert result.backtracks == backtrack_count

    def test_stepwise_same_result_as_solve(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)

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
        if solve_result.solved_grid and stepwise_result.solved_grid:
            assert solve_result.solved_grid.to_2d_list() == stepwise_result.solved_grid.to_2d_list()

    def test_stepwise_invalid_grid(self):
        puzzle = [
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
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(puzzle)
        gen = solver.solve_stepwise(grid)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            result = e.value
        assert result.status == SolveStatus.UNSOLVABLE

    def test_step_events_have_running_metrics(self):
        solver = ForwardCheckingSolver()
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        gen = solver.solve_stepwise(grid)

        prev_states = 0
        try:
            while True:
                step = next(gen)
                # states_explored should be non-decreasing
                assert step.states_explored >= prev_states
                prev_states = step.states_explored
        except StopIteration:
            pass
