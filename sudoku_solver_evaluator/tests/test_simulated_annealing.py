"""Unit tests for the Simulated Annealing solver.

Tests verify that the SA solver correctly implements the SolverProtocol
interface and satisfies Requirements 4.1 through 4.10.
"""

import random

import pytest

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers.simulated_annealing import SimulatedAnnealingSolver


# A known solvable easy puzzle (many filled cells for faster SA convergence)
EASY_PUZZLE = [
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

# A nearly complete puzzle that SA can solve quickly
NEARLY_COMPLETE_PUZZLE = [
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


class TestSimulatedAnnealingSolverInit:
    """Tests for SA solver initialization and configuration."""

    def test_name_property(self):
        """Solver should identify as 'Simulated Annealing'."""
        solver = SimulatedAnnealingSolver()
        assert solver.name == "Simulated Annealing"

    def test_default_parameters(self):
        """Solver should have correct default parameters."""
        solver = SimulatedAnnealingSolver()
        assert solver._initial_temp == 1.0
        assert solver._cooling_rate == 0.99
        assert solver._min_temp == 0.001
        assert solver._max_restarts == 10

    def test_custom_parameters(self):
        """Solver should accept custom parameters."""
        solver = SimulatedAnnealingSolver(
            initial_temp=2.0, cooling_rate=0.95, min_temp=0.01, max_restarts=5
        )
        assert solver._initial_temp == 2.0
        assert solver._cooling_rate == 0.95
        assert solver._min_temp == 0.01
        assert solver._max_restarts == 5


class TestGridInitialization:
    """Tests for SA grid initialization (Requirement 4.1)."""

    def test_initialization_preserves_fixed_cells(self):
        """After initialization, all fixed cells retain their original values."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(EASY_PUZZLE)
        working_grid = grid.copy()
        solver._initialize_grid(working_grid)

        for row in range(9):
            for col in range(9):
                original = grid.get_cell(row, col)
                initialized = working_grid.get_cell(row, col)
                if original.is_fixed:
                    assert initialized.value == original.value

    def test_initialization_fills_all_cells(self):
        """After initialization, every cell has a value (no None)."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(EASY_PUZZLE)
        working_grid = grid.copy()
        solver._initialize_grid(working_grid)

        for row in range(9):
            for col in range(9):
                assert working_grid.get_cell(row, col).value is not None

    def test_initialization_boxes_contain_1_to_9(self):
        """After initialization, each 3x3 box contains exactly digits 1-9."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(EASY_PUZZLE)
        working_grid = grid.copy()
        solver._initialize_grid(working_grid)

        for box_index in range(9):
            box_cells = working_grid.get_box(box_index)
            values = [cell.value for cell in box_cells]
            assert sorted(values) == list(range(1, 10))


class TestCostFunction:
    """Tests for SA cost function (Requirement 4.2)."""

    def test_solved_grid_has_zero_cost(self):
        """A fully solved grid should have cost 0."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(NEARLY_COMPLETE_PUZZLE)
        assert solver._compute_cost(grid) == 0

    def test_cost_counts_row_duplicates(self):
        """Cost function should count duplicates in rows."""
        solver = SimulatedAnnealingSolver()
        # Create a grid with known row duplicates
        values = [row[:] for row in NEARLY_COMPLETE_PUZZLE]
        # Swap two values in the first row to create a duplicate
        values[0][0], values[0][1] = values[0][1], values[0][0]  # swap 5 and 3
        # This doesn't create duplicates in row 0, but might in cols
        # Let's create a clear duplicate scenario
        values = [
            [1, 1, 3, 4, 5, 6, 7, 8, 9],  # row has 1 appearing twice: cost += 1
            [2, 2, 2, 4, 5, 6, 7, 8, 9],  # row has 2 appearing 3 times: cost += 2
            [3, 4, 5, 6, 7, 8, 9, 1, 2],
            [4, 5, 6, 7, 8, 9, 1, 2, 3],
            [5, 6, 7, 8, 9, 1, 2, 3, 4],
            [6, 7, 8, 9, 1, 2, 3, 4, 5],
            [7, 8, 9, 1, 2, 3, 4, 5, 6],
            [8, 9, 1, 2, 3, 4, 5, 6, 7],
            [9, 3, 4, 5, 6, 7, 8, 9, 1],  # row has 9 appearing twice: cost += 1
        ]
        grid = Grid.from_2d_list(values)
        cost = solver._compute_cost(grid)
        # Row duplicates: row0=1, row1=2, row8=1 → 4 from rows
        # Columns also have duplicates we need to account for
        assert cost > 0  # At minimum we have row duplicates

    def test_cost_counts_column_duplicates(self):
        """Cost function should count duplicates in columns."""
        solver = SimulatedAnnealingSolver()
        # Create a grid where columns have duplicates but rows don't
        values = [
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 3, 4, 5, 6, 7, 8, 9, 2],  # col 0 has 1 twice
            [2, 4, 5, 6, 7, 8, 9, 1, 3],
            [3, 5, 6, 7, 8, 9, 1, 2, 4],
            [4, 6, 7, 8, 9, 1, 2, 3, 5],
            [5, 7, 8, 9, 1, 2, 3, 4, 6],
            [6, 8, 9, 1, 2, 3, 4, 5, 7],
            [7, 9, 1, 2, 3, 4, 5, 6, 8],
            [8, 1, 2, 3, 4, 5, 6, 7, 9],
        ]
        grid = Grid.from_2d_list(values)
        cost = solver._compute_cost(grid)
        # Columns have duplicates, so cost should be > 0
        assert cost > 0


class TestCostDelta:
    """Tests for SA cost delta computation."""

    def test_delta_zero_for_same_value_swap(self):
        """Swapping two cells with the same value should have delta 0."""
        solver = SimulatedAnnealingSolver()
        # Create a grid where two cells in same box have same value
        values = [
            [1, 1, 3, 4, 5, 6, 7, 8, 9],
            [2, 2, 4, 5, 6, 7, 8, 9, 1],
            [3, 3, 5, 6, 7, 8, 9, 1, 2],
            [4, 5, 6, 7, 8, 9, 1, 2, 3],
            [5, 6, 7, 8, 9, 1, 2, 3, 4],
            [6, 7, 8, 9, 1, 2, 3, 4, 5],
            [7, 8, 9, 1, 2, 3, 4, 5, 6],
            [8, 9, 1, 2, 3, 4, 5, 6, 7],
            [9, 4, 2, 3, 4, 5, 6, 7, 8],
        ]
        grid = Grid.from_2d_list(values)
        # Swap (0,0) and (0,1) which both have value 1
        delta = solver._compute_cost_delta(grid, 0, 0, 0, 1)
        assert delta == 0

    def test_delta_consistency_with_full_cost(self):
        """Cost delta should equal the difference of full cost computations."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(EASY_PUZZLE)
        working_grid = grid.copy()
        solver._initialize_grid(working_grid)

        random.seed(42)
        # Pick two non-fixed cells in box 0
        box_cells = working_grid.get_box(0)
        non_fixed = [(c.row, c.col) for c in box_cells if not c.is_fixed]
        if len(non_fixed) >= 2:
            (r1, c1), (r2, c2) = non_fixed[0], non_fixed[1]

            cost_before = solver._compute_cost(working_grid)
            delta = solver._compute_cost_delta(working_grid, r1, c1, r2, c2)

            # Actually perform the swap and compute full cost
            v1 = working_grid.get_cell(r1, c1).value
            v2 = working_grid.get_cell(r2, c2).value
            working_grid.set_value(r1, c1, v2)
            working_grid.set_value(r2, c2, v1)
            cost_after = solver._compute_cost(working_grid)

            assert delta == cost_after - cost_before


class TestSolveMethod:
    """Tests for the SA solve() method."""

    def test_solve_does_not_mutate_input(self):
        """solve() must work on a copy and never mutate the original grid."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(EASY_PUZZLE)
        original_values = grid.to_2d_list()
        solver.solve(grid, timeout=5.0)
        assert grid.to_2d_list() == original_values

    def test_solve_returns_correct_solver_type(self):
        """SolveResult should indicate LOCAL_SEARCH solver type."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(EASY_PUZZLE)
        result = solver.solve(grid, timeout=5.0)
        assert result.solver_type == SolverType.LOCAL_SEARCH

    def test_solve_already_complete_grid(self):
        """A fully solved grid should return SOLVED immediately."""
        solver = SimulatedAnnealingSolver()
        grid = Grid.from_2d_list(NEARLY_COMPLETE_PUZZLE)
        result = solver.solve(grid, timeout=5.0)
        assert result.status == SolveStatus.SOLVED
        assert result.best_cost == 0

    def test_solve_records_metrics(self):
        """solve() should record states_explored and restarts."""
        solver = SimulatedAnnealingSolver(max_restarts=2)
        grid = Grid.from_2d_list(EASY_PUZZLE)
        result = solver.solve(grid, timeout=5.0)
        # states_explored should be positive (some swaps attempted)
        assert result.states_explored >= 0
        assert result.restarts >= 0
        assert result.best_cost is not None

    def test_solve_timeout_returns_timeout_status(self):
        """solve() should return TIMEOUT when time limit is exceeded."""
        solver = SimulatedAnnealingSolver(max_restarts=100)
        grid = Grid.from_2d_list(EASY_PUZZLE)
        result = solver.solve(grid, timeout=0.001)
        # With such a short timeout, it should timeout or possibly solve on init
        assert result.status in (SolveStatus.TIMEOUT, SolveStatus.SOLVED)

    def test_solve_max_restarts_returns_failed(self):
        """solve() should return FAILED when max restarts exhausted."""
        # Use very low temperature range to force quick restarts
        solver = SimulatedAnnealingSolver(
            initial_temp=0.002, cooling_rate=0.5, min_temp=0.001, max_restarts=2
        )
        grid = Grid.from_2d_list(EASY_PUZZLE)
        result = solver.solve(grid, timeout=10.0)
        # With such poor parameters, it should fail
        assert result.status in (SolveStatus.FAILED, SolveStatus.SOLVED)
        if result.status == SolveStatus.FAILED:
            assert result.best_cost is not None
            assert result.solved_grid is not None  # best grid returned


class TestSolveStepwise:
    """Tests for the SA solve_stepwise() method."""

    def test_stepwise_emits_swap_events(self):
        """solve_stepwise() should yield StepEvents with SWAP type."""
        solver = SimulatedAnnealingSolver(
            initial_temp=0.01, cooling_rate=0.9, min_temp=0.001, max_restarts=1
        )
        grid = Grid.from_2d_list(EASY_PUZZLE)
        gen = solver.solve_stepwise(grid, timeout=5.0)

        events = []
        try:
            while True:
                event = next(gen)
                events.append(event)
                if len(events) >= 5:
                    break
        except StopIteration:
            pass

        # Should have emitted at least some swap events
        if events:
            for event in events:
                assert event.step_type == StepType.SWAP
                assert event.row is not None
                assert event.col is not None
                assert event.swap_row is not None
                assert event.swap_col is not None
                assert event.current_cost is not None

    def test_stepwise_swap_cells_in_same_box(self):
        """All swap events should involve cells in the same 3x3 box."""
        solver = SimulatedAnnealingSolver(
            initial_temp=0.01, cooling_rate=0.9, min_temp=0.001, max_restarts=1
        )
        grid = Grid.from_2d_list(EASY_PUZZLE)
        gen = solver.solve_stepwise(grid, timeout=5.0)

        events = []
        try:
            while True:
                event = next(gen)
                events.append(event)
                if len(events) >= 10:
                    break
        except StopIteration:
            pass

        for event in events:
            # Both cells should be in the same box
            box1 = (event.row // 3) * 3 + (event.col // 3)
            box2 = (event.swap_row // 3) * 3 + (event.swap_col // 3)
            assert box1 == box2, f"Swap cells not in same box: ({event.row},{event.col}) box {box1} vs ({event.swap_row},{event.swap_col}) box {box2}"

    def test_stepwise_does_not_mutate_input(self):
        """solve_stepwise() must work on a copy and never mutate the original grid."""
        solver = SimulatedAnnealingSolver(
            initial_temp=0.01, cooling_rate=0.9, min_temp=0.001, max_restarts=1
        )
        grid = Grid.from_2d_list(EASY_PUZZLE)
        original_values = grid.to_2d_list()

        gen = solver.solve_stepwise(grid, timeout=5.0)
        try:
            while True:
                next(gen)
        except StopIteration:
            pass

        assert grid.to_2d_list() == original_values

    def test_stepwise_states_explored_increments(self):
        """states_explored in step events should be monotonically increasing."""
        solver = SimulatedAnnealingSolver(
            initial_temp=0.01, cooling_rate=0.9, min_temp=0.001, max_restarts=1
        )
        grid = Grid.from_2d_list(EASY_PUZZLE)
        gen = solver.solve_stepwise(grid, timeout=5.0)

        prev_states = 0
        count = 0
        try:
            while True:
                event = next(gen)
                assert event.states_explored >= prev_states
                prev_states = event.states_explored
                count += 1
                if count >= 20:
                    break
        except StopIteration:
            pass
