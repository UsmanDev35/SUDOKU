"""Simulated Annealing solver (local search).

This module implements a Simulated Annealing (SA) solver for Sudoku puzzles.
SA is a probabilistic local search technique that starts from a complete but
possibly inconsistent assignment and iteratively improves it by swapping
cell values within 3x3 boxes.

Algorithm Overview:
    1. Initialize each 3x3 box with a random permutation of 1-9, preserving
       pre-filled (fixed) cells in their original positions.
    2. Compute the initial cost: total duplicate values across all rows and columns.
    3. Main loop (until cost=0 or temperature < min_temp):
       a. Pick a random 3x3 box.
       b. Pick two random non-fixed cells within that box.
       c. Compute the cost delta if those cells were swapped.
       d. If delta <= 0 (better or equal): accept the swap.
       e. If delta > 0 (worse): accept with probability e^(-delta/temperature).
       f. Apply geometric cooling: T_new = T × cooling_rate.
       g. Track states_explored and best_cost.
    4. If cost reaches 0: return SOLVED.
    5. If temperature < min_temp: restart with new initialization (up to max_restarts).
    6. If max_restarts exhausted: return FAILED with best grid found.

The SA approach treats Sudoku as an optimization problem rather than a
constraint satisfaction problem. By initializing boxes correctly, the box
constraints are always satisfied. The cost function only measures row and
column violations, which the algorithm minimizes through local swaps.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10
"""

import math
import random
import time
from typing import Generator, Optional

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol


class SimulatedAnnealingSolver(SolverProtocol):
    """Local Search solver using Simulated Annealing.

    This solver treats Sudoku as an optimization problem. It starts with a
    complete (but possibly invalid) grid where each 3x3 box contains a valid
    permutation of 1-9, then iteratively reduces row/column conflicts by
    swapping non-fixed cells within boxes.

    The acceptance of worse solutions is controlled by a temperature parameter
    that decreases geometrically over time, allowing the algorithm to escape
    local minima early on while converging to a solution as temperature drops.

    Attributes:
        _initial_temp: Starting temperature for the annealing schedule.
        _cooling_rate: Multiplicative factor for geometric cooling (0 < rate < 1).
        _min_temp: Temperature threshold below which a restart is triggered.
        _max_restarts: Maximum number of restarts before declaring failure.
    """

    def __init__(
        self,
        initial_temp: float = 1.0,
        cooling_rate: float = 0.99,
        min_temp: float = 0.001,
        max_restarts: int = 10,
    ) -> None:
        """Initialize the SimulatedAnnealingSolver with configurable parameters.

        Args:
            initial_temp: Starting temperature. Higher values allow more
                exploration of worse states early on. Defaults to 1.0.
            cooling_rate: Factor by which temperature is multiplied each
                iteration. Must be between 0.0 (exclusive) and 1.0 (exclusive).
                Defaults to 0.99.
            min_temp: Temperature threshold below which the solver restarts
                with a new random initialization. Defaults to 0.001.
            max_restarts: Maximum number of restarts before returning FAILED.
                Defaults to 10.
        """
        self._initial_temp = initial_temp
        self._cooling_rate = cooling_rate
        self._min_temp = min_temp
        self._max_restarts = max_restarts

    @property
    def name(self) -> str:
        """Human-readable name of the solver.

        Returns:
            The string 'Simulated Annealing'.
        """
        return "Simulated Annealing"

    def _initialize_grid(self, grid: Grid) -> Grid:
        """Fill each 3x3 box with a random permutation of 1-9, preserving fixed cells.

        For each of the 9 boxes, this method:
        1. Identifies which values are already placed in fixed cells.
        2. Determines which values from 1-9 are missing.
        3. Randomly shuffles the missing values.
        4. Assigns them to the non-fixed (empty) cells in the box.

        After initialization, every box contains exactly the digits 1-9,
        satisfying box constraints. Row and column constraints may still
        be violated.

        Args:
            grid: A copy of the puzzle grid to initialize.

        Returns:
            The same grid object, now fully populated with values.

        Validates: Requirement 4.1
        """
        for box_index in range(9):
            # Get all cells in this 3x3 box
            box_cells = grid.get_box(box_index)

            # Identify values already placed by fixed cells
            fixed_values = set()
            non_fixed_cells = []
            for cell in box_cells:
                if cell.is_fixed:
                    fixed_values.add(cell.value)
                else:
                    non_fixed_cells.append(cell)

            # Determine which values 1-9 are missing from the box
            missing_values = list(set(range(1, 10)) - fixed_values)

            # Randomly shuffle the missing values for random initialization
            random.shuffle(missing_values)

            # Assign missing values to non-fixed cells
            for i, cell in enumerate(non_fixed_cells):
                grid.set_value(cell.row, cell.col, missing_values[i])

        return grid

    def _compute_cost(self, grid: Grid) -> int:
        """Compute the total cost: sum of duplicate values in all rows and columns.

        For each row and column, count how many times each value 1-9 appears.
        For each value that appears more than once, add (count - 1) to the cost.
        This means a value appearing twice adds 1, appearing three times adds 2, etc.

        A cost of 0 means no duplicates exist in any row or column, which
        (combined with valid box initialization) means the puzzle is solved.

        Args:
            grid: The current grid state to evaluate.

        Returns:
            Integer cost representing total row + column violations.

        Validates: Requirement 4.2
        """
        cost = 0

        # Count duplicates in each row
        for row in range(9):
            # Count occurrences of each value in this row
            value_counts: dict[int, int] = {}
            for col in range(9):
                val = grid.get_cell(row, col).value
                if val is not None:
                    value_counts[val] = value_counts.get(val, 0) + 1
            # Add (count - 1) for each value appearing more than once
            for count in value_counts.values():
                if count > 1:
                    cost += count - 1

        # Count duplicates in each column
        for col in range(9):
            # Count occurrences of each value in this column
            value_counts = {}
            for row in range(9):
                val = grid.get_cell(row, col).value
                if val is not None:
                    value_counts[val] = value_counts.get(val, 0) + 1
            # Add (count - 1) for each value appearing more than once
            for count in value_counts.values():
                if count > 1:
                    cost += count - 1

        return cost

    def _compute_cost_delta(
        self, grid: Grid, row1: int, col1: int, row2: int, col2: int
    ) -> int:
        """Compute the change in cost if two cells were swapped.

        Instead of recomputing the full cost after a swap, this method
        calculates only the difference by examining the affected rows and
        columns. This is an O(1) optimization compared to O(81) full recompute.

        The delta is computed as: cost_after_swap - cost_before_swap.
        A negative delta means the swap improves (reduces) the cost.

        Args:
            grid: The current grid state.
            row1: Row of the first cell.
            col1: Column of the first cell.
            row2: Row of the second cell.
            col2: Column of the second cell.

        Returns:
            Integer cost change (negative = improvement, positive = worsening).
        """
        val1 = grid.get_cell(row1, col1).value
        val2 = grid.get_cell(row2, col2).value

        # If both cells have the same value, swapping changes nothing
        if val1 == val2:
            return 0

        # Calculate cost contribution of affected rows/cols BEFORE swap
        cost_before = 0
        cost_before += self._row_cost(grid, row1)
        cost_before += self._row_cost(grid, row2)
        cost_before += self._col_cost(grid, col1)
        cost_before += self._col_cost(grid, col2)

        # Avoid double-counting if cells share a row or column
        if row1 == row2:
            cost_before -= self._row_cost(grid, row1)
        if col1 == col2:
            cost_before -= self._col_cost(grid, col1)

        # Perform the swap temporarily
        grid.set_value(row1, col1, val2)
        grid.set_value(row2, col2, val1)

        # Calculate cost contribution of affected rows/cols AFTER swap
        cost_after = 0
        cost_after += self._row_cost(grid, row1)
        cost_after += self._row_cost(grid, row2)
        cost_after += self._col_cost(grid, col1)
        cost_after += self._col_cost(grid, col2)

        # Avoid double-counting if cells share a row or column
        if row1 == row2:
            cost_after -= self._row_cost(grid, row1)
        if col1 == col2:
            cost_after -= self._col_cost(grid, col1)

        # Undo the swap to restore original state
        grid.set_value(row1, col1, val1)
        grid.set_value(row2, col2, val2)

        return cost_after - cost_before

    def _row_cost(self, grid: Grid, row: int) -> int:
        """Compute the duplicate cost for a single row.

        Args:
            grid: The current grid state.
            row: Row index (0-8).

        Returns:
            Sum of (count - 1) for each value appearing more than once in the row.
        """
        value_counts: dict[int, int] = {}
        for col in range(9):
            val = grid.get_cell(row, col).value
            if val is not None:
                value_counts[val] = value_counts.get(val, 0) + 1
        cost = 0
        for count in value_counts.values():
            if count > 1:
                cost += count - 1
        return cost

    def _col_cost(self, grid: Grid, col: int) -> int:
        """Compute the duplicate cost for a single column.

        Args:
            grid: The current grid state.
            col: Column index (0-8).

        Returns:
            Sum of (count - 1) for each value appearing more than once in the column.
        """
        value_counts: dict[int, int] = {}
        for row in range(9):
            val = grid.get_cell(row, col).value
            if val is not None:
                value_counts[val] = value_counts.get(val, 0) + 1
        cost = 0
        for count in value_counts.values():
            if count > 1:
                cost += count - 1
        return cost

    def _get_non_fixed_cells_in_box(self, grid: Grid, box_index: int) -> list[tuple[int, int]]:
        """Get coordinates of all non-fixed cells in a given box.

        Args:
            grid: The current grid state.
            box_index: Box index (0-8).

        Returns:
            List of (row, col) tuples for non-fixed cells in the box.
        """
        box_cells = grid.get_box(box_index)
        return [(cell.row, cell.col) for cell in box_cells if not cell.is_fixed]

    def solve(self, grid: Grid, timeout: float = 60.0) -> SolveResult:
        """Solve the given Sudoku puzzle using Simulated Annealing.

        Works on a deep copy of the input grid. Initializes each box with
        a random permutation of 1-9 (preserving fixed cells), then iteratively
        swaps non-fixed cells within boxes to minimize row/column conflicts.

        Uses geometric cooling schedule with restarts when temperature drops
        below the minimum threshold.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Returns:
            SolveResult containing:
                - SOLVED status with the completed grid if cost reaches 0.
                - TIMEOUT status with partial metrics if timeout is exceeded.
                - FAILED status with best grid found if max restarts exhausted.

        Validates: Requirements 4.1-4.10
        """
        start_time = time.monotonic()

        # Metrics tracking
        states_explored = 0
        restarts = 0
        best_cost: Optional[int] = None
        best_grid: Optional[Grid] = None

        # Pre-compute non-fixed cells per box (these don't change between restarts)
        # We need at least 2 non-fixed cells in a box to perform a swap
        working_grid = grid.copy()
        box_non_fixed: list[list[tuple[int, int]]] = []
        for box_index in range(9):
            box_non_fixed.append(self._get_non_fixed_cells_in_box(working_grid, box_index))

        # Identify boxes that have at least 2 non-fixed cells (swappable boxes)
        swappable_boxes = [i for i in range(9) if len(box_non_fixed[i]) >= 2]

        # If no boxes have 2+ non-fixed cells, we can't perform any swaps
        # Check if the grid is already solved after initialization
        if not swappable_boxes:
            working_grid = self._initialize_grid(working_grid)
            current_cost = self._compute_cost(working_grid)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            if current_cost == 0:
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.SOLVED,
                    solved_grid=working_grid,
                    time_ms=elapsed_ms,
                    states_explored=0,
                    restarts=0,
                    best_cost=0,
                )
            else:
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.FAILED,
                    solved_grid=working_grid,
                    time_ms=elapsed_ms,
                    states_explored=0,
                    restarts=0,
                    best_cost=current_cost,
                )

        # Main loop with restarts (Requirement 4.8)
        while restarts <= self._max_restarts:
            # Check timeout before each restart
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.TIMEOUT,
                    solved_grid=best_grid,
                    time_ms=elapsed_ms,
                    states_explored=states_explored,
                    restarts=restarts,
                    best_cost=best_cost,
                )

            # Initialize grid with random permutation in each box (Requirement 4.1)
            working_grid = grid.copy()
            self._initialize_grid(working_grid)

            # Compute initial cost (Requirement 4.2)
            current_cost = self._compute_cost(working_grid)

            # Track best cost and grid across all restarts (Requirement 4.9)
            if best_cost is None or current_cost < best_cost:
                best_cost = current_cost
                best_grid = working_grid.copy()

            # Check if already solved after initialization
            if current_cost == 0:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.SOLVED,
                    solved_grid=working_grid,
                    time_ms=elapsed_ms,
                    states_explored=states_explored,
                    restarts=restarts,
                    best_cost=0,
                )

            # Initialize temperature for this restart
            temperature = self._initial_temp

            # Annealing loop: iterate until cost=0 or temperature < min_temp
            while temperature >= self._min_temp:
                # Check timeout (Requirement 6.5)
                if time.monotonic() - start_time >= timeout:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    return SolveResult(
                        solver_type=SolverType.LOCAL_SEARCH,
                        status=SolveStatus.TIMEOUT,
                        solved_grid=best_grid,
                        time_ms=elapsed_ms,
                        states_explored=states_explored,
                        restarts=restarts,
                        best_cost=best_cost,
                    )

                # Select a random box that has at least 2 non-fixed cells (Requirement 4.3)
                box_index = random.choice(swappable_boxes)
                non_fixed = box_non_fixed[box_index]

                # Pick two distinct random non-fixed cells within that box (Requirement 4.3)
                idx1, idx2 = random.sample(range(len(non_fixed)), 2)
                row1, col1 = non_fixed[idx1]
                row2, col2 = non_fixed[idx2]

                # Compute cost delta for the proposed swap
                delta = self._compute_cost_delta(working_grid, row1, col1, row2, col2)

                # Increment states_explored for each swap attempted (Requirement 4.10)
                states_explored += 1

                # Acceptance criterion (Requirements 4.4, 4.5)
                accept = False
                if delta <= 0:
                    # Accept better or equal moves always (Requirement 4.4)
                    accept = True
                else:
                    # Accept worse moves with probability e^(-delta/T) (Requirement 4.5)
                    acceptance_probability = math.exp(-delta / temperature)
                    if random.random() < acceptance_probability:
                        accept = True

                # Apply or reject the swap
                if accept:
                    # Perform the swap
                    val1 = working_grid.get_cell(row1, col1).value
                    val2 = working_grid.get_cell(row2, col2).value
                    working_grid.set_value(row1, col1, val2)
                    working_grid.set_value(row2, col2, val1)
                    current_cost += delta

                    # Update best cost tracking (Requirement 4.9)
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_grid = working_grid.copy()

                    # Check if solved (Requirement 4.7)
                    if current_cost == 0:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(
                            solver_type=SolverType.LOCAL_SEARCH,
                            status=SolveStatus.SOLVED,
                            solved_grid=working_grid,
                            time_ms=elapsed_ms,
                            states_explored=states_explored,
                            restarts=restarts,
                            best_cost=0,
                        )

                # Geometric cooling (Requirement 4.6): T_new = T × cooling_rate
                temperature *= self._cooling_rate

            # Temperature reached minimum threshold - restart (Requirement 4.8)
            restarts += 1

        # Max restarts exhausted - return FAILED with best grid (Requirement 4.9)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return SolveResult(
            solver_type=SolverType.LOCAL_SEARCH,
            status=SolveStatus.FAILED,
            solved_grid=best_grid,
            time_ms=elapsed_ms,
            states_explored=states_explored,
            restarts=restarts,
            best_cost=best_cost,
        )

    def solve_stepwise(
        self, grid: Grid, timeout: float = 60.0
    ) -> Generator[StepEvent, None, SolveResult]:
        """Solve the puzzle yielding StepEvents for each swap operation.

        This method implements the same SA algorithm as solve() but yields
        a StepEvent with SWAP type for each accepted swap operation. This
        enables the UI to display step-by-step progress showing which cells
        are being swapped and the current cost.

        The StepEvent includes:
            - step_type: SWAP
            - row, col: coordinates of the first cell
            - swap_row, swap_col: coordinates of the second cell
            - current_cost: cost after the swap

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Yields:
            StepEvent with step_type SWAP for each accepted swap operation.

        Returns:
            SolveResult upon completion (same semantics as solve()).

        Validates: Requirements 4.1-4.10
        """
        start_time = time.monotonic()

        # Metrics tracking
        states_explored = 0
        restarts = 0
        best_cost: Optional[int] = None
        best_grid: Optional[Grid] = None

        # Pre-compute non-fixed cells per box
        working_grid = grid.copy()
        box_non_fixed: list[list[tuple[int, int]]] = []
        for box_index in range(9):
            box_non_fixed.append(self._get_non_fixed_cells_in_box(working_grid, box_index))

        # Identify swappable boxes (at least 2 non-fixed cells)
        swappable_boxes = [i for i in range(9) if len(box_non_fixed[i]) >= 2]

        # Edge case: no swappable boxes
        if not swappable_boxes:
            working_grid = self._initialize_grid(working_grid)
            current_cost = self._compute_cost(working_grid)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            if current_cost == 0:
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.SOLVED,
                    solved_grid=working_grid,
                    time_ms=elapsed_ms,
                    states_explored=0,
                    restarts=0,
                    best_cost=0,
                )
            else:
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.FAILED,
                    solved_grid=working_grid,
                    time_ms=elapsed_ms,
                    states_explored=0,
                    restarts=0,
                    best_cost=current_cost,
                )

        # Main loop with restarts
        while restarts <= self._max_restarts:
            # Check timeout
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.TIMEOUT,
                    solved_grid=best_grid,
                    time_ms=elapsed_ms,
                    states_explored=states_explored,
                    restarts=restarts,
                    best_cost=best_cost,
                )

            # Initialize grid with random permutation in each box
            working_grid = grid.copy()
            self._initialize_grid(working_grid)

            # Compute initial cost
            current_cost = self._compute_cost(working_grid)

            # Track best cost and grid
            if best_cost is None or current_cost < best_cost:
                best_cost = current_cost
                best_grid = working_grid.copy()

            # Check if already solved
            if current_cost == 0:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.LOCAL_SEARCH,
                    status=SolveStatus.SOLVED,
                    solved_grid=working_grid,
                    time_ms=elapsed_ms,
                    states_explored=states_explored,
                    restarts=restarts,
                    best_cost=0,
                )

            # Initialize temperature
            temperature = self._initial_temp

            # Annealing loop
            while temperature >= self._min_temp:
                # Check timeout
                if time.monotonic() - start_time >= timeout:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    return SolveResult(
                        solver_type=SolverType.LOCAL_SEARCH,
                        status=SolveStatus.TIMEOUT,
                        solved_grid=best_grid,
                        time_ms=elapsed_ms,
                        states_explored=states_explored,
                        restarts=restarts,
                        best_cost=best_cost,
                    )

                # Select random swappable box and two non-fixed cells
                box_index = random.choice(swappable_boxes)
                non_fixed = box_non_fixed[box_index]
                idx1, idx2 = random.sample(range(len(non_fixed)), 2)
                row1, col1 = non_fixed[idx1]
                row2, col2 = non_fixed[idx2]

                # Compute cost delta
                delta = self._compute_cost_delta(working_grid, row1, col1, row2, col2)

                # Increment states_explored
                states_explored += 1

                # Acceptance criterion
                accept = False
                if delta <= 0:
                    accept = True
                else:
                    acceptance_probability = math.exp(-delta / temperature)
                    if random.random() < acceptance_probability:
                        accept = True

                # Apply or reject the swap
                if accept:
                    val1 = working_grid.get_cell(row1, col1).value
                    val2 = working_grid.get_cell(row2, col2).value
                    working_grid.set_value(row1, col1, val2)
                    working_grid.set_value(row2, col2, val1)
                    current_cost += delta

                    # Update best cost tracking
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_grid = working_grid.copy()

                    # Emit SWAP step event for visualization (Requirement 9.3)
                    yield StepEvent(
                        step_type=StepType.SWAP,
                        row=row1,
                        col=col1,
                        value=val2,
                        previous_value=val1,
                        swap_row=row2,
                        swap_col=col2,
                        states_explored=states_explored,
                        current_cost=current_cost,
                    )

                    # Check if solved
                    if current_cost == 0:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(
                            solver_type=SolverType.LOCAL_SEARCH,
                            status=SolveStatus.SOLVED,
                            solved_grid=working_grid,
                            time_ms=elapsed_ms,
                            states_explored=states_explored,
                            restarts=restarts,
                            best_cost=0,
                        )

                # Geometric cooling
                temperature *= self._cooling_rate

            # Temperature reached minimum - restart
            restarts += 1

        # Max restarts exhausted - return FAILED with best grid
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return SolveResult(
            solver_type=SolverType.LOCAL_SEARCH,
            status=SolveStatus.FAILED,
            solved_grid=best_grid,
            time_ms=elapsed_ms,
            states_explored=states_explored,
            restarts=restarts,
            best_cost=best_cost,
        )
