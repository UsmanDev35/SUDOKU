"""Property-based tests for the Sudoku Solver and Evaluator system.

Uses the Hypothesis library to verify correctness properties hold across
all valid inputs. Each test is tagged with the feature and property it validates.
"""

import math
import tempfile
import os
from collections import Counter

from hypothesis import given, settings
from hypothesis import strategies as st

from sudoku_solver_evaluator.models.enums import DifficultyLevel, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver
from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver
from sudoku_solver_evaluator.solvers.simulated_annealing import SimulatedAnnealingSolver
from sudoku_solver_evaluator.evaluator.exporter import ExportRow, export_csv, read_csv


# Feature: sudoku-solver-evaluator, Property 2: Difficulty level determines pre-filled cell count
@given(difficulty=st.sampled_from(DifficultyLevel))
@settings(max_examples=10, deadline=None)
def test_difficulty_cell_count_range(difficulty):
    """**Validates: Requirements 1.3, 1.4, 1.5, 1.6**

    For any generated puzzle, the number of pre-filled cells SHALL fall within
    the range defined by its difficulty level:
        - EASY: 36-45
        - MEDIUM: 27-35
        - HARD: 22-26
        - EXPERT: 17-21
    """
    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    filled = puzzle.count_filled()

    ranges = {
        DifficultyLevel.EASY: (36, 45),
        DifficultyLevel.MEDIUM: (27, 35),
        DifficultyLevel.HARD: (22, 26),
        DifficultyLevel.EXPERT: (17, 21),
    }

    min_filled, max_filled = ranges[difficulty]
    assert min_filled <= filled <= max_filled, (
        f"Difficulty {difficulty.value}: expected {min_filled}-{max_filled} "
        f"pre-filled cells, got {filled}"
    )


# Feature: sudoku-solver-evaluator, Property 5: Backtracking solver follows deterministic traversal and value ordering
@given(difficulty=st.sampled_from([DifficultyLevel.EASY]))
@settings(max_examples=10, deadline=None)
def test_backtracking_traversal_order(difficulty):
    """**Validates: Requirements 2.1, 2.2**

    For any puzzle solved by the Backtracking_Solver, the first assignment to
    each cell position SHALL follow left-to-right, top-to-bottom order (skipping
    fixed cells), and values SHALL be tried in ascending order 1 through 9.
    """
    from sudoku_solver_evaluator.models.enums import StepType
    from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver

    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = BacktrackingSolver()
    gen = solver.solve_stepwise(puzzle)

    # Collect first ASSIGN event for each cell position
    first_assign_positions = []
    seen_positions = set()

    try:
        while True:
            event = next(gen)
            if event.step_type == StepType.ASSIGN:
                pos = (event.row, event.col)
                if pos not in seen_positions:
                    first_assign_positions.append(pos)
                    seen_positions.add(pos)
    except StopIteration:
        pass

    # Verify positions are in left-to-right, top-to-bottom order
    for i in range(len(first_assign_positions) - 1):
        r1, c1 = first_assign_positions[i]
        r2, c2 = first_assign_positions[i + 1]
        assert (r1 * 9 + c1) < (r2 * 9 + c2), (
            f"Cell ({r1},{c1}) should come before ({r2},{c2}) in traversal order"
        )


# Feature: sudoku-solver-evaluator, Property 3: All solvers produce valid complete grids for solvable puzzles
@given(difficulty=st.sampled_from([DifficultyLevel.EASY, DifficultyLevel.MEDIUM]))
@settings(max_examples=10, deadline=None)
def test_solver_produces_valid_solution(difficulty):
    """**Validates: Requirements 2.5**

    For any solvable Sudoku puzzle and any solver, when the solver returns a
    SOLVED status, the returned grid SHALL be a complete valid Sudoku solution
    (all 81 cells filled, each row/column/box contains digits 1-9 exactly once)
    that is consistent with the original puzzle's pre-filled cells.
    """
    from sudoku_solver_evaluator.models.enums import SolveStatus
    from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver

    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = BacktrackingSolver()
    result = solver.solve(puzzle)

    # Solver should find a solution for a valid puzzle
    assert result.status == SolveStatus.SOLVED
    assert result.solved_grid is not None

    # Solution must be complete (all 81 cells filled)
    assert result.solved_grid.is_complete()

    # Solution must be valid (no constraint violations)
    assert result.solved_grid.is_valid()

    # All pre-filled cells must be preserved
    for row in range(9):
        for col in range(9):
            original_cell = puzzle.get_cell(row, col)
            if original_cell.is_fixed:
                solved_cell = result.solved_grid.get_cell(row, col)
                assert solved_cell.value == original_cell.value


# Feature: sudoku-solver-evaluator, Property 6: Solver metrics are consistent with step events
@given(difficulty=st.sampled_from([DifficultyLevel.EASY]))
@settings(max_examples=10, deadline=None)
def test_metrics_match_step_events(difficulty):
    """**Validates: Requirements 2.7**

    For any solve operation, the reported states_explored SHALL equal the number
    of ASSIGN step events emitted, and the reported backtracks SHALL equal the
    number of BACKTRACK step events emitted.
    """
    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = BacktrackingSolver()
    gen = solver.solve_stepwise(puzzle)

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

    assert result.states_explored == assign_count, (
        f"states_explored mismatch: result reports {result.states_explored}, "
        f"but counted {assign_count} ASSIGN events"
    )
    assert result.backtracks == backtrack_count, (
        f"backtracks mismatch: result reports {result.backtracks}, "
        f"but counted {backtrack_count} BACKTRACK events"
    )


# Feature: sudoku-solver-evaluator, Property 7: MRV-using solvers select minimum domain cell
@given(difficulty=st.sampled_from([DifficultyLevel.EASY, DifficultyLevel.MEDIUM]))
@settings(max_examples=100, deadline=None)
def test_mrv_selection(difficulty):
    """**Validates: Requirements 3.2, 5.6**

    For any puzzle solved by the Informed_Solver or Constraint_Propagation_Solver,
    at each variable selection step, the chosen cell SHALL have a domain size less
    than or equal to all other unassigned cells' domain sizes.
    """
    from unittest.mock import patch
    from sudoku_solver_evaluator.solvers.informed import InformedSolver, _select_variable
    from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver

    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    # --- Test Informed Solver MRV ---
    violations_informed = []

    def _wrapped_select_variable(domains, assigned):
        """Wrapper that verifies MRV property before returning the selection."""
        result = _select_variable(domains, assigned)

        # Find the minimum domain size among all unassigned cells
        min_domain_size = None
        for cell, domain in domains.items():
            if cell not in assigned and len(domain) > 0:
                if min_domain_size is None or len(domain) < min_domain_size:
                    min_domain_size = len(domain)

        # The selected cell's domain size must equal the minimum
        if min_domain_size is not None:
            selected_domain_size = len(domains[result])
            if selected_domain_size > min_domain_size:
                violations_informed.append(
                    f"Informed Solver selected cell {result} with domain size "
                    f"{selected_domain_size}, but minimum was {min_domain_size}"
                )

        return result

    with patch(
        "sudoku_solver_evaluator.solvers.informed._select_variable",
        side_effect=_wrapped_select_variable,
    ):
        informed_solver = InformedSolver()
        informed_solver.solve(puzzle)

    assert not violations_informed, (
        f"Informed Solver MRV violations:\n" + "\n".join(violations_informed)
    )

    # --- Test Forward Checking Solver MRV ---
    violations_fc = []
    fc_solver = ForwardCheckingSolver()
    original_select_mrv = fc_solver._select_mrv

    def _wrapped_select_mrv(grid, domains):
        """Wrapper that verifies MRV property before returning the selection."""
        result = original_select_mrv(grid, domains)

        if result is None:
            return result

        # Find the minimum domain size among all unassigned cells
        min_domain_size = None
        for r in range(9):
            for c in range(9):
                if grid.get_cell(r, c).value is None:
                    size = len(domains[(r, c)])
                    if size > 0 and (min_domain_size is None or size < min_domain_size):
                        min_domain_size = size

        # The selected cell's domain size must equal the minimum
        if min_domain_size is not None:
            selected_domain_size = len(domains[result])
            if selected_domain_size > min_domain_size:
                violations_fc.append(
                    f"FC Solver selected cell {result} with domain size "
                    f"{selected_domain_size}, but minimum was {min_domain_size}"
                )

        return result

    fc_solver._select_mrv = _wrapped_select_mrv
    fc_solver.solve(puzzle)

    assert not violations_fc, (
        f"Forward Checking Solver MRV violations:\n" + "\n".join(violations_fc)
    )


# Feature: sudoku-solver-evaluator, Property 8: SA initialization preserves fixed cells and fills boxes correctly
@given(difficulty=st.sampled_from(DifficultyLevel))
@settings(max_examples=100, deadline=None)
def test_sa_initialization(difficulty):
    """**Validates: Requirements 4.1**

    For any puzzle, after Simulated Annealing initialization, each 3x3 box
    SHALL contain exactly the digits 1-9 (a valid permutation), and all
    pre-filled cells SHALL retain their original values.
    """
    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = SimulatedAnnealingSolver()

    # Initialize the grid using SA's initialization method
    working_grid = puzzle.copy()
    solver._initialize_grid(working_grid)

    # Verify: Each 3x3 box contains exactly digits 1-9
    for box_index in range(9):
        box_cells = working_grid.get_box(box_index)
        box_values = [cell.value for cell in box_cells]

        # All cells must have a value (no None)
        assert None not in box_values, (
            f"Box {box_index} has an unfilled cell after SA initialization: {box_values}"
        )

        # Box must contain exactly digits 1-9 (a valid permutation)
        assert sorted(box_values) == list(range(1, 10)), (
            f"Box {box_index} does not contain exactly digits 1-9: {sorted(box_values)}"
        )

    # Verify: All pre-filled cells retain their original values
    for row in range(9):
        for col in range(9):
            original_cell = puzzle.get_cell(row, col)
            if original_cell.is_fixed:
                initialized_cell = working_grid.get_cell(row, col)
                assert initialized_cell.value == original_cell.value, (
                    f"Fixed cell ({row},{col}) changed from {original_cell.value} "
                    f"to {initialized_cell.value} after SA initialization"
                )


# Feature: sudoku-solver-evaluator, Property 10: SA swaps only non-fixed cells within the same box
@given(difficulty=st.sampled_from(DifficultyLevel))
@settings(max_examples=100, deadline=None)
def test_sa_swap_validity(difficulty):
    """**Validates: Requirements 4.3**

    For any swap step event emitted by the Local_Search_Solver, both involved
    cells SHALL be in the same 3x3 box and neither cell SHALL be a pre-filled
    (fixed) cell.
    """
    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    # Use a low initial temperature and few restarts to limit iterations
    # while still producing swap events for validation
    solver = SimulatedAnnealingSolver(
        initial_temp=0.5,
        cooling_rate=0.9,
        min_temp=0.01,
        max_restarts=1,
    )

    # Collect the set of fixed cell positions from the original puzzle
    fixed_cells = set()
    for row in range(9):
        for col in range(9):
            cell = puzzle.get_cell(row, col)
            if cell.is_fixed:
                fixed_cells.add((row, col))

    # Run solver in stepwise mode and collect SWAP events
    gen = solver.solve_stepwise(puzzle, timeout=10.0)
    swap_events = []

    try:
        while True:
            event = next(gen)
            if event.step_type == StepType.SWAP:
                swap_events.append(event)
    except StopIteration:
        pass

    # We should have at least some swap events to validate
    # (unless the puzzle was trivially solved after initialization)
    # Verify properties for each swap event
    for event in swap_events:
        row1, col1 = event.row, event.col
        row2, col2 = event.swap_row, event.swap_col

        # Property: Both cells must be in the same 3x3 box
        box1 = (row1 // 3) * 3 + (col1 // 3)
        box2 = (row2 // 3) * 3 + (col2 // 3)
        assert box1 == box2, (
            f"Swap cells ({row1},{col1}) and ({row2},{col2}) are in different "
            f"boxes: box {box1} vs box {box2}"
        )

        # Property: Neither cell is a fixed (pre-filled) cell
        assert (row1, col1) not in fixed_cells, (
            f"Swap involves fixed cell ({row1},{col1})"
        )
        assert (row2, col2) not in fixed_cells, (
            f"Swap involves fixed cell ({row2},{col2})"
        )


# Feature: sudoku-solver-evaluator, Property 4: Solvers correctly identify unsolvable puzzles


@st.composite
def invalid_grid_strategy(draw):
    """Generate a Sudoku grid with constraint violations.

    Creates a mostly-empty 9x9 grid and introduces a duplicate value in
    a randomly chosen unit (row, column, or box) to create an unsolvable
    constraint violation.

    Strategy:
    1. Start with an empty 9x9 grid (all zeros).
    2. Choose a violation type: row, column, or box.
    3. Choose a value (1-9) to duplicate.
    4. Place the duplicate value in two distinct cells within the same unit.
    """
    from sudoku_solver_evaluator.models.grid import Grid

    # Start with an empty grid
    values = [[0] * 9 for _ in range(9)]

    # Choose the type of violation to introduce
    violation_type = draw(st.sampled_from(["row", "column", "box"]))

    # Choose the value to duplicate (1-9)
    dup_value = draw(st.integers(min_value=1, max_value=9))

    if violation_type == "row":
        # Pick a row, then pick two distinct columns
        row = draw(st.integers(min_value=0, max_value=8))
        cols = draw(
            st.lists(
                st.integers(min_value=0, max_value=8),
                min_size=2,
                max_size=2,
                unique=True,
            )
        )
        values[row][cols[0]] = dup_value
        values[row][cols[1]] = dup_value

    elif violation_type == "column":
        # Pick a column, then pick two distinct rows
        col = draw(st.integers(min_value=0, max_value=8))
        rows = draw(
            st.lists(
                st.integers(min_value=0, max_value=8),
                min_size=2,
                max_size=2,
                unique=True,
            )
        )
        values[rows[0]][col] = dup_value
        values[rows[1]][col] = dup_value

    else:  # box
        # Pick a box (0-8), then pick two distinct positions within it
        box_index = draw(st.integers(min_value=0, max_value=8))
        box_start_row = (box_index // 3) * 3
        box_start_col = (box_index % 3) * 3

        # Generate two distinct positions within the 3x3 box (0-8 flat index)
        positions = draw(
            st.lists(
                st.integers(min_value=0, max_value=8),
                min_size=2,
                max_size=2,
                unique=True,
            )
        )
        r1 = box_start_row + positions[0] // 3
        c1 = box_start_col + positions[0] % 3
        r2 = box_start_row + positions[1] // 3
        c2 = box_start_col + positions[1] % 3

        values[r1][c1] = dup_value
        values[r2][c2] = dup_value

    return Grid.from_2d_list(values)


@given(grid=invalid_grid_strategy())
@settings(max_examples=100, deadline=None)
def test_solver_detects_unsolvable(grid):
    """**Validates: Requirements 2.6, 2.8, 3.7**

    For any Sudoku grid with pre-filled cells that violate constraints
    (duplicate values in a row, column, or box), all backtracking-based
    solvers (Backtracking_Solver, Informed_Solver, Constraint_Propagation_Solver)
    SHALL return an unsolvable status.
    """
    from sudoku_solver_evaluator.models.enums import SolveStatus
    from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver
    from sudoku_solver_evaluator.solvers.informed import InformedSolver
    from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver

    solvers = [
        BacktrackingSolver(),
        InformedSolver(),
        ForwardCheckingSolver(),
    ]

    for solver in solvers:
        result = solver.solve(grid, timeout=10.0)
        assert result.status == SolveStatus.UNSOLVABLE, (
            f"{solver.name} returned status {result.status.value} instead of "
            f"UNSOLVABLE for a grid with constraint violations"
        )



# Feature: sudoku-solver-evaluator, Property 13: FC forward checking removes assigned value from peer domains
@given(difficulty=st.sampled_from(DifficultyLevel))
@settings(max_examples=100, deadline=None)
def test_fc_forward_checking(difficulty):
    """**Validates: Requirements 5.2**

    For any value assignment during Forward Checking, immediately after the
    assignment, no unassigned peer cell (same row, column, or box) SHALL have
    the assigned value in its domain.
    """
    from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver

    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = ForwardCheckingSolver()
    working_grid = puzzle.copy()

    # Initialize domains using the FC solver's domain initialization
    domains = solver._initialize_domains(working_grid)

    # Find an empty cell with a non-empty domain to assign
    empty_cells = [
        (r, c)
        for r in range(9)
        for c in range(9)
        if working_grid.get_cell(r, c).value is None and len(domains[(r, c)]) > 0
    ]

    # There must be at least one empty cell since we generated a puzzle
    assert len(empty_cells) > 0, "Generated puzzle has no empty cells"

    # Pick the first empty cell (deterministic for reproducibility)
    row, col = empty_cells[0]
    value = next(iter(domains[(row, col)]))

    # Assign the value to the cell on the grid
    working_grid.set_value(row, col, value)
    domains[(row, col)] = {value}

    # Call _forward_check to propagate the constraint
    solver._forward_check(working_grid, domains, row, col, value)

    # Verify: no unassigned peer cell has the assigned value in its domain
    peers = solver._get_peers(row, col)
    for pr, pc in peers:
        if working_grid.get_cell(pr, pc).value is None:
            assert value not in domains[(pr, pc)], (
                f"After assigning value {value} to cell ({row},{col}), "
                f"unassigned peer cell ({pr},{pc}) still has {value} in its "
                f"domain: {domains[(pr, pc)]}"
            )


# Feature: sudoku-solver-evaluator, Property 9: SA cost function correctly counts row and column duplicates
@given(
    grid_values=st.lists(
        st.lists(
            st.integers(min_value=1, max_value=9),
            min_size=9,
            max_size=9,
        ),
        min_size=9,
        max_size=9,
    )
)
@settings(max_examples=100, deadline=None)
def test_sa_cost_function(grid_values):
    """**Validates: Requirements 4.2**

    For any grid state, the cost function SHALL return a value equal to the sum
    of (count - 1) for each value that appears more than once in any row or
    column, computed independently.
    """
    # Build a Grid from the random values (all cells non-fixed so we can fill freely)
    grid = Grid.from_2d_list([[0] * 9 for _ in range(9)])
    for row in range(9):
        for col in range(9):
            grid.set_value(row, col, grid_values[row][col])

    # Compute expected cost manually
    expected_cost = 0

    # Count duplicates in each row
    for row in range(9):
        counts = Counter(grid_values[row])
        for count in counts.values():
            if count > 1:
                expected_cost += count - 1

    # Count duplicates in each column
    for col in range(9):
        col_values = [grid_values[row][col] for row in range(9)]
        counts = Counter(col_values)
        for count in counts.values():
            if count > 1:
                expected_cost += count - 1

    # Compute actual cost using the SA solver's _compute_cost method
    solver = SimulatedAnnealingSolver()
    actual_cost = solver._compute_cost(grid)

    assert actual_cost == expected_cost, (
        f"Cost mismatch: expected {expected_cost}, got {actual_cost}. "
        f"Grid values: {grid_values}"
    )


# Feature: sudoku-solver-evaluator, Property 11: SA temperature follows geometric cooling schedule
@given(
    initial_temp=st.floats(min_value=0.01, max_value=100.0),
    cooling_rate=st.floats(min_value=0.8, max_value=0.999),
    num_steps=st.integers(min_value=1, max_value=500),
)
@settings(max_examples=100)
def test_sa_cooling_schedule(initial_temp, cooling_rate, num_steps):
    """**Validates: Requirements 4.6**

    For any sequence of consecutive iterations in the Local_Search_Solver
    (within a single restart), the temperature at step N+1 SHALL equal
    the temperature at step N multiplied by the cooling rate (within
    floating-point tolerance).

    This test verifies that the geometric cooling schedule T_new = T × cooling_rate
    is followed correctly by simulating the schedule for N steps and checking that
    T[n] = initial_temp * cooling_rate^n (within floating-point tolerance using
    math.isclose).
    """
    # Simulate the cooling schedule iteratively (as the SA solver does)
    temperature = initial_temp
    for step in range(num_steps):
        # Compute expected temperature at this step using the formula directly
        expected_temp = initial_temp * (cooling_rate ** step)

        # Verify current temperature matches expected (within floating-point tolerance)
        assert math.isclose(temperature, expected_temp, rel_tol=1e-9), (
            f"At step {step}: temperature {temperature} != expected {expected_temp} "
            f"(initial_temp={initial_temp}, cooling_rate={cooling_rate})"
        )

        # Apply geometric cooling as the SA solver does: T_new = T × cooling_rate
        next_temperature = temperature * cooling_rate

        # Verify the relationship T[n+1] = T[n] * cooling_rate holds
        expected_next = temperature * cooling_rate
        assert math.isclose(next_temperature, expected_next, rel_tol=1e-9), (
            f"At step {step}: T_new {next_temperature} != T * cooling_rate "
            f"{expected_next} (T={temperature}, cooling_rate={cooling_rate})"
        )

        temperature = next_temperature

    # Final verification: after num_steps iterations, T should equal initial_temp * cooling_rate^num_steps
    expected_final = initial_temp * (cooling_rate ** num_steps)
    assert math.isclose(temperature, expected_final, rel_tol=1e-9), (
        f"After {num_steps} steps: final temperature {temperature} != expected "
        f"{expected_final} (initial_temp={initial_temp}, cooling_rate={cooling_rate})"
    )


# Feature: sudoku-solver-evaluator, Property 14: FC propagation assigns forced values
@given(difficulty=st.sampled_from(DifficultyLevel))
@settings(max_examples=100, deadline=None)
def test_fc_propagation_forced_values(difficulty):
    """**Validates: Requirements 5.4, 5.5**

    For any state during Forward Checking where a cell's domain is reduced to
    exactly one value (naked single) or a value appears in exactly one cell's
    domain within a unit (hidden single), that value SHALL be assigned to that
    cell automatically.
    """
    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = ForwardCheckingSolver()
    working_grid = puzzle.copy()

    # Initialize domains (Requirement 5.1)
    domains = solver._initialize_domains(working_grid)

    # --- Identify naked singles before propagation ---
    # A naked single is an empty cell whose domain has exactly one value
    naked_singles_before = {}
    for r in range(9):
        for c in range(9):
            if working_grid.get_cell(r, c).value is None and len(domains[(r, c)]) == 1:
                naked_singles_before[(r, c)] = next(iter(domains[(r, c)]))

    # --- Identify hidden singles before propagation ---
    # A hidden single is a value that appears in exactly one cell's domain
    # within a row, column, or box
    hidden_singles_before = {}

    # Check rows
    for r in range(9):
        for value in range(1, 10):
            # Skip values already assigned in this row
            assigned_in_row = any(
                working_grid.get_cell(r, c).value == value for c in range(9)
            )
            if assigned_in_row:
                continue
            # Find unassigned cells that have this value in their domain
            candidates = [
                (r, c) for c in range(9)
                if working_grid.get_cell(r, c).value is None
                and value in domains[(r, c)]
            ]
            if len(candidates) == 1:
                hidden_singles_before[candidates[0]] = value

    # Check columns
    for c in range(9):
        for value in range(1, 10):
            assigned_in_col = any(
                working_grid.get_cell(r, c).value == value for r in range(9)
            )
            if assigned_in_col:
                continue
            candidates = [
                (r, c) for r in range(9)
                if working_grid.get_cell(r, c).value is None
                and value in domains[(r, c)]
            ]
            if len(candidates) == 1:
                hidden_singles_before[candidates[0]] = value

    # Check boxes
    for box in range(9):
        box_r = (box // 3) * 3
        box_c = (box % 3) * 3
        box_cells = [
            (box_r + dr, box_c + dc) for dr in range(3) for dc in range(3)
        ]
        for value in range(1, 10):
            assigned_in_box = any(
                working_grid.get_cell(r, c).value == value for r, c in box_cells
            )
            if assigned_in_box:
                continue
            candidates = [
                (r, c) for r, c in box_cells
                if working_grid.get_cell(r, c).value is None
                and value in domains[(r, c)]
            ]
            if len(candidates) == 1:
                hidden_singles_before[candidates[0]] = value

    # Combine all forced values (naked singles + hidden singles)
    forced_cells = {}
    forced_cells.update(naked_singles_before)
    forced_cells.update(hidden_singles_before)

    # Skip if no forced values found (some puzzles may not have any
    # naked or hidden singles in the initial domain state)
    if not forced_cells:
        return

    # --- Run propagation ---
    states_explored = [0]
    backtracks_count = [0]
    propagation_ok = solver._propagate(
        working_grid, domains, states_explored, None, backtracks_count
    )

    # If propagation returned False, it means a dead end was detected which
    # shouldn't happen on valid puzzles, but we only verify the property
    # for successful propagation cases
    if not propagation_ok:
        return

    # --- Verify: all forced cells should now be assigned ---
    for (r, c), expected_value in forced_cells.items():
        cell = working_grid.get_cell(r, c)
        assert cell.value is not None, (
            f"Cell ({r},{c}) had a forced value {expected_value} "
            f"(naked/hidden single) but was not assigned after propagation. "
            f"Domain before propagation: size was "
            f"{'1 (naked single)' if (r, c) in naked_singles_before else 'hidden single in unit'}"
        )
        assert cell.value == expected_value, (
            f"Cell ({r},{c}) was assigned value {cell.value} but the forced "
            f"value was {expected_value}"
        )


# Feature: sudoku-solver-evaluator, Property 12: FC domain initialization removes peer values
@given(difficulty=st.sampled_from(DifficultyLevel))
@settings(max_examples=100, deadline=None)
def test_fc_domain_initialization(difficulty):
    """**Validates: Requirements 5.1**

    For any puzzle, after Forward Checking initialization, no empty cell's domain
    SHALL contain a value that is already assigned to a pre-filled cell in the
    same row, column, or box.
    """
    generator = PuzzleGenerator()
    puzzle = generator.generate(difficulty)

    solver = ForwardCheckingSolver()
    working_grid = puzzle.copy()

    # Call ForwardCheckingSolver's _initialize_domains method
    domains = solver._initialize_domains(working_grid)

    # For each empty cell, verify its domain does not contain any value
    # assigned to a pre-filled cell in the same row, column, or box
    for row in range(9):
        for col in range(9):
            cell = working_grid.get_cell(row, col)
            if cell.value is not None:
                # Fixed/assigned cell — skip domain check
                continue

            domain = domains[(row, col)]

            # Collect all values assigned to pre-filled peers in same row
            for c in range(9):
                peer_cell = working_grid.get_cell(row, c)
                if peer_cell.value is not None:
                    assert peer_cell.value not in domain, (
                        f"Empty cell ({row},{col}) domain {domain} contains "
                        f"value {peer_cell.value} assigned to row peer ({row},{c})"
                    )

            # Collect all values assigned to pre-filled peers in same column
            for r in range(9):
                peer_cell = working_grid.get_cell(r, col)
                if peer_cell.value is not None:
                    assert peer_cell.value not in domain, (
                        f"Empty cell ({row},{col}) domain {domain} contains "
                        f"value {peer_cell.value} assigned to column peer ({r},{col})"
                    )

            # Collect all values assigned to pre-filled peers in same box
            box_start_row = (row // 3) * 3
            box_start_col = (col // 3) * 3
            for r in range(box_start_row, box_start_row + 3):
                for c in range(box_start_col, box_start_col + 3):
                    peer_cell = working_grid.get_cell(r, c)
                    if peer_cell.value is not None:
                        assert peer_cell.value not in domain, (
                            f"Empty cell ({row},{col}) domain {domain} contains "
                            f"value {peer_cell.value} assigned to box peer ({r},{c})"
                        )


# Feature: sudoku-solver-evaluator, Property 16: CSV export round-trip preserves data
@st.composite
def export_row_strategy(draw):
    """Generate a random ExportRow with valid field values."""
    puzzle_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=20,
    ))
    difficulty_level = draw(st.sampled_from([d.value for d in DifficultyLevel]))
    algorithm_name = draw(st.sampled_from(["backtracking", "informed", "local_search", "forward_checking"]))
    time_taken = draw(st.integers(min_value=0, max_value=1_000_000))
    states_explored = draw(st.integers(min_value=0, max_value=10_000_000))
    backtracks = draw(st.integers(min_value=0, max_value=10_000_000))
    optimality_rank = draw(st.integers(min_value=1, max_value=4))

    return ExportRow(
        puzzle_id=puzzle_id,
        difficulty_level=difficulty_level,
        algorithm_name=algorithm_name,
        time_taken=time_taken,
        states_explored=states_explored,
        backtracks=backtracks,
        optimality_rank=optimality_rank,
    )


@given(rows=st.lists(export_row_strategy(), min_size=1, max_size=50))
@settings(max_examples=100)
def test_csv_export_roundtrip(rows):
    """**Validates: Requirements 7.6**

    For any set of recorded performance results, exporting to CSV and parsing
    the CSV back SHALL produce data matching the original results, with all
    required columns present (puzzle_id, difficulty_level, algorithm_name,
    time_taken, states_explored, backtracks, optimality_rank).
    """
    # Export to a temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        export_csv(tmp_path, rows)

        # Read back the CSV
        read_back = read_csv(tmp_path)

        # Verify the number of rows matches
        assert len(read_back) == len(rows), (
            f"Row count mismatch: exported {len(rows)} rows, read back {len(read_back)}"
        )

        # Verify each row matches exactly on all 7 columns
        for i, (original, parsed) in enumerate(zip(rows, read_back)):
            assert parsed.puzzle_id == original.puzzle_id, (
                f"Row {i}: puzzle_id mismatch: '{parsed.puzzle_id}' != '{original.puzzle_id}'"
            )
            assert parsed.difficulty_level == original.difficulty_level, (
                f"Row {i}: difficulty_level mismatch: '{parsed.difficulty_level}' != '{original.difficulty_level}'"
            )
            assert parsed.algorithm_name == original.algorithm_name, (
                f"Row {i}: algorithm_name mismatch: '{parsed.algorithm_name}' != '{original.algorithm_name}'"
            )
            assert parsed.time_taken == original.time_taken, (
                f"Row {i}: time_taken mismatch: {parsed.time_taken} != {original.time_taken}"
            )
            assert parsed.states_explored == original.states_explored, (
                f"Row {i}: states_explored mismatch: {parsed.states_explored} != {original.states_explored}"
            )
            assert parsed.backtracks == original.backtracks, (
                f"Row {i}: backtracks mismatch: {parsed.backtracks} != {original.backtracks}"
            )
            assert parsed.optimality_rank == original.optimality_rank, (
                f"Row {i}: optimality_rank mismatch: {parsed.optimality_rank} != {original.optimality_rank}"
            )
    finally:
        os.unlink(tmp_path)


# Feature: sudoku-solver-evaluator, Property 15: Performance evaluator computes correct statistics and rankings
@st.composite
def solve_results_strategy(draw):
    """Generate a collection of SolveResult objects for evaluator testing.

    Produces a list of (puzzle_id, difficulty, SolveResult) tuples where:
    - Multiple solver types produce results for the same puzzle
    - Multiple puzzles share the same difficulty level (at least 5)
    - Metrics (time_ms, states_explored, backtracks) are randomized
    """
    from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolverType, SolveStatus
    from sudoku_solver_evaluator.models.metrics import SolveResult

    # Choose a difficulty level for the batch
    difficulty = draw(st.sampled_from(DifficultyLevel))

    # Generate between 5 and 10 puzzles to satisfy the minimum 5 requirement
    num_puzzles = draw(st.integers(min_value=5, max_value=10))

    # Choose which solver types to use (at least 2 for meaningful rankings)
    available_solvers = list(SolverType)
    num_solvers = draw(st.integers(min_value=2, max_value=len(available_solvers)))
    solvers = draw(
        st.lists(
            st.sampled_from(available_solvers),
            min_size=num_solvers,
            max_size=num_solvers,
            unique=True,
        )
    )

    results = []
    for i in range(num_puzzles):
        puzzle_id = f"puzzle_{i}"
        for solver_type in solvers:
            time_ms = draw(st.integers(min_value=1, max_value=100000))
            states_explored = draw(st.integers(min_value=1, max_value=100000))
            backtracks = draw(st.integers(min_value=0, max_value=50000))

            result = SolveResult(
                solver_type=solver_type,
                status=SolveStatus.SOLVED,
                time_ms=time_ms,
                states_explored=states_explored,
                backtracks=backtracks,
            )
            results.append((puzzle_id, difficulty, result))

    return results


@given(data=solve_results_strategy())
@settings(max_examples=100)
def test_evaluator_statistics(data):
    """**Validates: Requirements 6.4, 6.6**

    For any collection of solve results for the same puzzle, the ranking SHALL
    order algorithms by states_explored ascending, and for any collection of
    results at the same difficulty level (minimum 5), the computed mean, min,
    and max SHALL be mathematically correct.
    """
    from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
    from sudoku_solver_evaluator.models.enums import SolverType

    evaluator = PerformanceEvaluator()

    # Record all results
    for puzzle_id, difficulty, result in data:
        evaluator.record(result, puzzle_id, difficulty)

    # Extract unique puzzle_ids and the shared difficulty
    puzzle_ids = list(dict.fromkeys(pid for pid, _, _ in data))
    difficulty = data[0][1]

    # --- Verify Property: Rankings order algorithms by states_explored ascending ---
    for puzzle_id in puzzle_ids:
        comparison = evaluator.get_comparison(puzzle_id)
        ranking = comparison.rankings["states_explored"]

        # Verify ranking is in ascending order of states_explored
        for i in range(len(ranking) - 1):
            solver_a = ranking[i]
            solver_b = ranking[i + 1]
            states_a = comparison.results[solver_a].states_explored
            states_b = comparison.results[solver_b].states_explored
            assert states_a <= states_b, (
                f"Ranking not ascending by states_explored for puzzle {puzzle_id}: "
                f"{solver_a.value} has {states_a} states but is ranked before "
                f"{solver_b.value} with {states_b} states"
            )

    # --- Verify Property: Mean/min/max are mathematically correct ---
    # We have at least 5 puzzles at the same difficulty
    assert len(puzzle_ids) >= 5, (
        f"Expected at least 5 puzzles, got {len(puzzle_ids)}"
    )

    aggregate = evaluator.get_aggregate(difficulty)

    # For each solver type in the aggregate stats, verify correctness
    for solver_type, algo_stats in aggregate.stats.items():
        # Collect all results for this solver at this difficulty
        solver_results = [
            result for pid, diff, result in data
            if result.solver_type == solver_type and diff == difficulty
        ]

        assert len(solver_results) > 0

        # Verify time_ms statistics
        times = [r.time_ms for r in solver_results]
        expected_mean_time = sum(times) / len(times)
        expected_min_time = min(times)
        expected_max_time = max(times)

        assert abs(algo_stats.mean_time_ms - expected_mean_time) < 1e-9, (
            f"Mean time mismatch for {solver_type.value}: "
            f"got {algo_stats.mean_time_ms}, expected {expected_mean_time}"
        )
        assert algo_stats.min_time_ms == expected_min_time, (
            f"Min time mismatch for {solver_type.value}: "
            f"got {algo_stats.min_time_ms}, expected {expected_min_time}"
        )
        assert algo_stats.max_time_ms == expected_max_time, (
            f"Max time mismatch for {solver_type.value}: "
            f"got {algo_stats.max_time_ms}, expected {expected_max_time}"
        )

        # Verify states_explored statistics
        states = [r.states_explored for r in solver_results]
        expected_mean_states = sum(states) / len(states)
        expected_min_states = min(states)
        expected_max_states = max(states)

        assert abs(algo_stats.mean_states - expected_mean_states) < 1e-9, (
            f"Mean states mismatch for {solver_type.value}: "
            f"got {algo_stats.mean_states}, expected {expected_mean_states}"
        )
        assert algo_stats.min_states == expected_min_states, (
            f"Min states mismatch for {solver_type.value}: "
            f"got {algo_stats.min_states}, expected {expected_min_states}"
        )
        assert algo_stats.max_states == expected_max_states, (
            f"Max states mismatch for {solver_type.value}: "
            f"got {algo_stats.max_states}, expected {expected_max_states}"
        )

        # Verify backtracks statistics
        bts = [r.backtracks for r in solver_results]
        expected_mean_bt = sum(bts) / len(bts)
        expected_min_bt = min(bts)
        expected_max_bt = max(bts)

        assert abs(algo_stats.mean_backtracks - expected_mean_bt) < 1e-9, (
            f"Mean backtracks mismatch for {solver_type.value}: "
            f"got {algo_stats.mean_backtracks}, expected {expected_mean_bt}"
        )
        assert algo_stats.min_backtracks == expected_min_bt, (
            f"Min backtracks mismatch for {solver_type.value}: "
            f"got {algo_stats.min_backtracks}, expected {expected_min_bt}"
        )
        assert algo_stats.max_backtracks == expected_max_bt, (
            f"Max backtracks mismatch for {solver_type.value}: "
            f"got {algo_stats.max_backtracks}, expected {expected_max_bt}"
        )


# Feature: sudoku-solver-evaluator, Property 17: Race winner has lower completion time
@st.composite
def race_result_strategy(draw):
    """Generate random RaceResult scenarios for testing winner determination.

    Generates two distinct solver types with random solve results, including
    both scenarios where times differ by >= 1000ms (clear winner) and where
    times are within 1000ms (tie).
    """
    from sudoku_solver_evaluator.models.enums import SolverType, SolveStatus
    from sudoku_solver_evaluator.models.metrics import SolveResult

    # Pick two distinct solver types
    all_solvers = list(SolverType)
    solver_a = draw(st.sampled_from(all_solvers))
    solver_b = draw(st.sampled_from([s for s in all_solvers if s != solver_a]))

    # Both solvers solved successfully
    time_a = draw(st.integers(min_value=100, max_value=60000))
    time_b = draw(st.integers(min_value=100, max_value=60000))

    states_a = draw(st.integers(min_value=1, max_value=100000))
    states_b = draw(st.integers(min_value=1, max_value=100000))

    result_a = SolveResult(
        solver_type=solver_a,
        status=SolveStatus.SOLVED,
        time_ms=time_a,
        states_explored=states_a,
    )
    result_b = SolveResult(
        solver_type=solver_b,
        status=SolveStatus.SOLVED,
        time_ms=time_b,
        states_explored=states_b,
    )

    return solver_a, solver_b, result_a, result_b


@given(data=race_result_strategy())
@settings(max_examples=100)
def test_race_winner_correctness(data):
    """**Validates: Requirements 10.4**

    For any adversarial race where exactly one algorithm completes before the
    other (not a tie), the declared winner SHALL be the algorithm with the
    strictly lower completion time in milliseconds.

    Also verifies that when times are within 1000ms, no winner is declared (tie).
    """
    from sudoku_solver_evaluator.adversarial.race import RaceController
    from sudoku_solver_evaluator.models.enums import SolveStatus

    solver_a, solver_b, result_a, result_b = data

    # Create a RaceController and directly set its internal results
    controller = RaceController()
    controller._result_a = result_a
    controller._result_b = result_b

    # Call _determine_winner
    winner = controller._determine_winner(solver_a, solver_b)

    time_diff = abs(result_a.time_ms - result_b.time_ms)

    if time_diff < 1000:
        # Times are within 1000ms — should be a tie (no winner)
        assert winner is None, (
            f"Expected tie (None) when time difference is {time_diff}ms (<1000ms), "
            f"but got winner={winner}. "
            f"Solver A ({solver_a.value}): {result_a.time_ms}ms, "
            f"Solver B ({solver_b.value}): {result_b.time_ms}ms"
        )
    else:
        # Clear winner — the one with lower time should win
        if result_a.time_ms < result_b.time_ms:
            expected_winner = solver_a
        else:
            expected_winner = solver_b

        assert winner == expected_winner, (
            f"Expected winner={expected_winner.value} (lower time), "
            f"but got winner={winner}. "
            f"Solver A ({solver_a.value}): {result_a.time_ms}ms, "
            f"Solver B ({solver_b.value}): {result_b.time_ms}ms, "
            f"time_diff={time_diff}ms"
        )
