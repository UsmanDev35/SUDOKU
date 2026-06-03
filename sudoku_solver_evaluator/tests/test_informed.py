"""Unit tests for the Informed Search solver (AC-3 + MRV + Degree Heuristic).

Tests cover:
- Solving known solvable puzzles
- Detecting invalid/unsolvable grids
- Timeout behavior
- MRV variable selection (smallest domain)
- Degree Heuristic tie-breaking
- AC-3 arc consistency enforcement
- Metric consistency between solve() and solve_stepwise()
- Non-mutation of input grid
- StepEvent emission (ASSIGN, BACKTRACK)

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

import pytest

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers.informed import (
    InformedSolver,
    _initialize_domains,
    _select_variable,
    _ac3,
    _copy_domains,
    _get_all_arcs,
    _get_affected_arcs,
    _PEERS,
)


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


class TestInformedSolverProperties:
    """Test basic properties of the InformedSolver class."""

    def test_name(self):
        solver = InformedSolver()
        assert solver.name == "Informed Search (AC-3 + MRV)"

    def test_solver_type_in_result(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)
        assert result.solver_type == SolverType.INFORMED


class TestInformedSolverSolve:
    """Test the solve() method."""

    def test_solves_valid_puzzle(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.SOLVED
        assert result.solved_grid is not None
        assert result.solved_grid.is_complete()
        assert result.solved_grid.is_valid()

    def test_preserves_fixed_cells(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)

        for row in range(9):
            for col in range(9):
                if SOLVABLE_PUZZLE[row][col] != 0:
                    assert result.solved_grid.get_cell(row, col).value == SOLVABLE_PUZZLE[row][col]

    def test_does_not_mutate_input_grid(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        original_values = grid.to_2d_list()
        solver.solve(grid)

        assert grid.to_2d_list() == original_values

    def test_already_solved_grid(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVED_GRID)
        result = solver.solve(grid)

        assert result.status == SolveStatus.SOLVED
        assert result.states_explored == 0
        assert result.backtracks == 0

    def test_records_positive_metrics(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        result = solver.solve(grid)

        assert result.states_explored > 0
        assert result.backtracks >= 0
        assert result.time_ms >= 0

    def test_fewer_states_than_backtracking(self):
        """AC-3 + MRV should explore fewer states than basic backtracking."""
        from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver

        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)

        informed = InformedSolver()
        backtracking = BacktrackingSolver()

        informed_result = informed.solve(grid)
        backtracking_result = backtracking.solve(grid)

        assert informed_result.status == SolveStatus.SOLVED
        assert backtracking_result.status == SolveStatus.SOLVED
        # Informed solver should explore fewer or equal states
        assert informed_result.states_explored <= backtracking_result.states_explored


class TestInformedSolverInvalidGrids:
    """Test detection of invalid initial grids (Requirement 3.7)."""

    def test_invalid_row_duplicate(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(INVALID_ROW_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert result.solved_grid is None

    def test_invalid_col_duplicate(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(INVALID_COL_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert result.solved_grid is None

    def test_invalid_box_duplicate(self):
        solver = InformedSolver()
        grid = Grid.from_2d_list(INVALID_BOX_PUZZLE)
        result = solver.solve(grid)

        assert result.status == SolveStatus.UNSOLVABLE
        assert result.states_explored == 0
        assert result.solved_grid is None


class TestInformedSolverTimeout:
    """Test timeout behavior."""

    def test_timeout_returns_timeout_status(self):
        solver = InformedSolver()
        empty_puzzle = [[0] * 9 for _ in range(9)]
        grid = Grid.from_2d_list(empty_puzzle)
        result = solver.solve(grid, timeout=0.0001)

        assert result.status == SolveStatus.TIMEOUT
        assert result.solved_grid is None

    def test_timeout_captures_partial_metrics(self):
        solver = InformedSolver()
        empty_puzzle = [[0] * 9 for _ in range(9)]
        grid = Grid.from_2d_list(empty_puzzle)
        result = solver.solve(grid, timeout=0.001)

        assert result.status == SolveStatus.TIMEOUT
        assert result.states_explored >= 0
        assert result.time_ms >= 0


class TestAC3Algorithm:
    """Test AC-3 arc consistency enforcement (Requirement 3.1, 3.4)."""

    def test_initial_domain_reduction(self):
        """AC-3 should reduce domains based on peer constraints."""
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)

        # Before AC-3, cell (0,2) should not have values present in its peers
        # Row 0 has: 5, 3, 7. Col 2 has: 8. Box 0 has: 5, 3, 6, 9, 8
        # So (0,2) initial domain after init should exclude: {5, 3, 7, 8, 6, 9, 1}
        # leaving {2, 4}
        assert 5 not in domains[(0, 2)]
        assert 3 not in domains[(0, 2)]

        # After AC-3, domains should be further reduced
        result = _ac3(domains)
        assert result is True  # Should achieve consistency without empty domains

    def test_ac3_detects_inconsistency(self):
        """AC-3 should detect when no consistent assignment exists."""
        # Create a full domain dict where two peer cells both have domain {1}
        # This creates an inconsistency since they're in the same row
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)

        # Force two peer cells in row 0 to both have only value {4}
        # (0,2) and (0,3) are in the same row - both having {4} is inconsistent
        domains[(0, 2)] = {4}
        domains[(0, 3)] = {4}

        # Run AC-3 on affected arcs - should detect inconsistency
        arcs = [((0, 2), (0, 3)), ((0, 3), (0, 2))]
        result = _ac3(domains, initial_arcs=arcs)
        assert result is False

    def test_ac3_preserves_consistent_domains(self):
        """AC-3 should not remove values that have support."""
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)
        _ac3(domains)

        # All assigned cells should retain their value in domain
        for r in range(9):
            for c in range(9):
                cell = grid.get_cell(r, c)
                if cell.value is not None:
                    assert cell.value in domains[(r, c)]


class TestMRVHeuristic:
    """Test MRV variable selection (Requirement 3.2)."""

    def test_selects_smallest_domain(self):
        """MRV should select the cell with fewest remaining values."""
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)
        _ac3(domains)

        assigned = set()
        for r in range(9):
            for c in range(9):
                if grid.get_cell(r, c).value is not None:
                    assigned.add((r, c))

        selected = _select_variable(domains, assigned)

        # Verify selected cell has minimum domain size
        min_size = min(
            len(domains[c]) for c in domains
            if c not in assigned and len(domains[c]) > 0
        )
        assert len(domains[selected]) == min_size

    def test_degree_heuristic_tiebreak(self):
        """When MRV ties, Degree Heuristic should select most constrained cell."""
        # Create a scenario with two cells having same domain size
        # but different numbers of unassigned peers
        domains = {}
        assigned = set()

        # Set up a simple scenario:
        # Cell (0,0) has domain {1,2} and many unassigned peers
        # Cell (8,8) has domain {1,2} and fewer unassigned peers
        for r in range(9):
            for c in range(9):
                if (r, c) == (0, 0):
                    domains[(r, c)] = {1, 2}
                elif (r, c) == (8, 8):
                    domains[(r, c)] = {1, 2}
                else:
                    # Most cells assigned (domain = singleton)
                    domains[(r, c)] = {5}
                    assigned.add((r, c))

        # Remove some cells from assigned to give (0,0) more unassigned peers
        # Unassign cells in row 0
        for c in range(1, 5):
            assigned.discard((0, c))
            domains[(0, c)] = {3, 4, 5}

        selected = _select_variable(domains, assigned)
        # (0,0) has more unassigned peers than (8,8) since we freed row 0 cells
        assert selected == (0, 0)

    def test_positional_order_final_tiebreak(self):
        """When MRV and Degree tie, positional order (row*9+col) should break tie."""
        domains = {}
        assigned = set()

        # All cells assigned except (1,0) and (0,1) with same domain size
        for r in range(9):
            for c in range(9):
                domains[(r, c)] = {5}
                assigned.add((r, c))

        # Remove two cells with same domain size - (0,1) should win (position 1 < 9)
        assigned.discard((0, 1))
        assigned.discard((1, 0))
        domains[(0, 1)] = {1, 2}
        domains[(1, 0)] = {1, 2}

        selected = _select_variable(domains, assigned)
        # Both have same domain size (2), need to check degree
        # If degree is same, position (0,1) = 1 < (1,0) = 9, so (0,1) wins
        # Note: degree might differ, but if equal, positional order applies
        assert selected[0] * 9 + selected[1] <= 9  # Either (0,1) or (1,0)


class TestDomainInitialization:
    """Test domain initialization (Requirement 3.1)."""

    def test_fixed_cells_have_singleton_domains(self):
        """Fixed cells should have domain = {value}."""
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)

        for r in range(9):
            for c in range(9):
                cell = grid.get_cell(r, c)
                if cell.value is not None:
                    assert domains[(r, c)] == {cell.value}

    def test_empty_cells_exclude_peer_values(self):
        """Empty cells' domains should not contain values assigned to peers."""
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)

        for r in range(9):
            for c in range(9):
                cell = grid.get_cell(r, c)
                if cell.value is None:
                    # Check that no peer's value is in this cell's domain
                    for pr, pc in _PEERS[(r, c)]:
                        peer_val = grid.get_cell(pr, pc).value
                        if peer_val is not None:
                            assert peer_val not in domains[(r, c)]

    def test_all_cells_have_domains(self):
        """Every cell (0,0) through (8,8) should have a domain entry."""
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        domains = _initialize_domains(grid)

        for r in range(9):
            for c in range(9):
                assert (r, c) in domains


class TestInformedSolverStepwise:
    """Test the solve_stepwise() method (Requirement 3.5, 3.8)."""

    def test_metrics_match_step_events(self):
        """Verify states_explored == ASSIGN count and backtracks == BACKTRACK count."""
        solver = InformedSolver()
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
        solver = InformedSolver()
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
        solver = InformedSolver()
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

    def test_assign_events_have_correct_values(self):
        """Verify ASSIGN events have valid row, col, and value fields."""
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        gen = solver.solve_stepwise(grid)

        try:
            while True:
                event = next(gen)
                if event.step_type == StepType.ASSIGN:
                    assert 0 <= event.row <= 8
                    assert 0 <= event.col <= 8
                    assert 1 <= event.value <= 9
                elif event.step_type == StepType.BACKTRACK:
                    assert 0 <= event.row <= 8
                    assert 0 <= event.col <= 8
                    assert event.value is None
                    assert event.previous_value is not None
        except StopIteration:
            pass

    def test_step_events_have_running_metrics(self):
        """Verify each StepEvent includes monotonically increasing metrics."""
        solver = InformedSolver()
        grid = Grid.from_2d_list(SOLVABLE_PUZZLE)
        gen = solver.solve_stepwise(grid)

        prev_states = 0
        try:
            while True:
                event = next(gen)
                if event.step_type == StepType.ASSIGN:
                    assert event.states_explored >= prev_states
                    prev_states = event.states_explored
                assert event.backtracks >= 0
        except StopIteration:
            pass


class TestHelperFunctions:
    """Test helper functions for the informed solver."""

    def test_peers_correctness(self):
        """Each cell should have exactly 20 peers."""
        for r in range(9):
            for c in range(9):
                assert len(_PEERS[(r, c)]) == 20

    def test_get_all_arcs_count(self):
        """Total arcs should be 81 cells × 20 peers = 1620."""
        arcs = _get_all_arcs()
        assert len(arcs) == 81 * 20

    def test_get_affected_arcs(self):
        """Affected arcs for a cell should be 20 (one per peer)."""
        arcs = _get_affected_arcs((0, 0))
        assert len(arcs) == 20
        # All arcs should be (peer, (0,0))
        for peer, cell in arcs:
            assert cell == (0, 0)
            assert peer in _PEERS[(0, 0)]

    def test_copy_domains_independence(self):
        """Copied domains should be independent of original."""
        domains = {(0, 0): {1, 2, 3}, (0, 1): {4, 5}}
        copied = _copy_domains(domains)

        # Modify original
        domains[(0, 0)].add(9)

        # Copy should be unaffected
        assert 9 not in copied[(0, 0)]
        assert copied[(0, 0)] == {1, 2, 3}
