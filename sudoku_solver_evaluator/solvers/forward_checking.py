"""Constraint Propagation solver with Forward Checking.

This module implements a Sudoku solver that combines constraint propagation
techniques (Naked Singles, Hidden Singles) with Forward Checking and the
Minimum Remaining Values (MRV) heuristic for variable selection.

Algorithm Overview:
    1. Initialize domains for all empty cells by removing values already
       assigned in peer cells (same row, column, or box).
    2. Apply initial propagation (Naked Singles + Hidden Singles) iteratively
       until a fixpoint is reached (no more changes).
    3. Begin recursive search:
       a. If all cells are assigned, return SOLVED.
       b. Select the next variable using MRV (smallest domain among unassigned).
       c. For each value in the selected cell's domain:
          - Save domain state (deep copy).
          - Assign value to cell.
          - Forward Check: remove value from all peer domains.
          - Apply Naked Singles + Hidden Singles propagation to fixpoint.
          - If no domain becomes empty, recurse.
          - If any domain becomes empty, restore domains and try next value.
       d. If no value works, backtrack.

Key Techniques:
    - Forward Checking: When a value is assigned, immediately remove that
      value from the domains of all unassigned peers. This detects failures
      early before exploring deeper.
    - Naked Singles: When a cell's domain is reduced to exactly one value,
      that value must be assigned automatically.
    - Hidden Singles: When a value appears in exactly one cell's domain
      within a unit (row, column, or box), assign it to that cell.
    - MRV Heuristic: Always choose the unassigned cell with the fewest
      remaining domain values, reducing the branching factor.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9
"""

import copy
import time
from typing import Generator, Optional

from sudoku_solver_evaluator.constraints.validator import is_grid_valid
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol


class ForwardCheckingSolver(SolverProtocol):
    """Constraint Propagation solver with Forward Checking.

    This solver combines domain-based constraint propagation with recursive
    backtracking search. It maintains a domain (set of possible values) for
    each unassigned cell and uses three propagation techniques to prune the
    search space:

    1. Forward Checking - removes assigned values from peer domains
    2. Naked Singles - auto-assigns cells with single-value domains
    3. Hidden Singles - assigns values that can only go in one cell in a unit

    The MRV (Minimum Remaining Values) heuristic is used for variable
    selection, always choosing the cell with the fewest remaining candidates.

    Attributes:
        _name: Human-readable name identifying this solver.
    """

    def __init__(self) -> None:
        """Initialize the ForwardCheckingSolver."""
        self._name = "Forward Checking"

    @property
    def name(self) -> str:
        """Human-readable name of the solver.

        Returns:
            The string 'Forward Checking'.
        """
        return self._name

    def _get_peers(self, row: int, col: int) -> list[tuple[int, int]]:
        """Get all peer cell coordinates for a given cell.

        Peers are cells in the same row, column, or 3x3 box (excluding
        the cell itself).

        Args:
            row: Row index (0-8).
            col: Column index (0-8).

        Returns:
            List of (row, col) tuples for all peer cells.
        """
        peers: set[tuple[int, int]] = set()

        # Same row
        for c in range(9):
            if c != col:
                peers.add((row, c))

        # Same column
        for r in range(9):
            if r != row:
                peers.add((r, col))

        # Same 3x3 box
        box_start_row = (row // 3) * 3
        box_start_col = (col // 3) * 3
        for r in range(box_start_row, box_start_row + 3):
            for c in range(box_start_col, box_start_col + 3):
                if (r, c) != (row, col):
                    peers.add((r, c))

        return list(peers)

    def _initialize_domains(
        self, grid: Grid
    ) -> dict[tuple[int, int], set[int]]:
        """Initialize domains for all cells based on current grid state.

        For each empty cell, the domain starts as {1..9} minus values already
        assigned in the same row, column, or box. For fixed cells, the domain
        is {value}. (Requirement 5.1)

        Args:
            grid: The current grid state.

        Returns:
            Dictionary mapping (row, col) to the set of possible values.
        """
        domains: dict[tuple[int, int], set[int]] = {}

        for r in range(9):
            for c in range(9):
                cell = grid.get_cell(r, c)
                if cell.value is not None:
                    domains[(r, c)] = {cell.value}
                else:
                    domain = set(range(1, 10))

                    # Remove values from same row
                    for cc in range(9):
                        val = grid.get_cell(r, cc).value
                        if val is not None:
                            domain.discard(val)

                    # Remove values from same column
                    for rr in range(9):
                        val = grid.get_cell(rr, c).value
                        if val is not None:
                            domain.discard(val)

                    # Remove values from same 3x3 box
                    box_r = (r // 3) * 3
                    box_c = (c // 3) * 3
                    for rr in range(box_r, box_r + 3):
                        for cc in range(box_c, box_c + 3):
                            val = grid.get_cell(rr, cc).value
                            if val is not None:
                                domain.discard(val)

                    domains[(r, c)] = domain

        return domains

    def _forward_check(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        row: int,
        col: int,
        value: int,
    ) -> bool:
        """Remove assigned value from all peer domains (Forward Checking).

        When a value is assigned to a cell, that value is removed from the
        domains of all unassigned peers (same row, column, box). If any peer
        domain becomes empty, the assignment is invalid. (Requirement 5.2)

        Args:
            grid: The current grid state.
            domains: The current domain mapping.
            row: Row of the assigned cell.
            col: Column of the assigned cell.
            value: The value that was assigned.

        Returns:
            True if all peer domains remain non-empty, False if any domain
            becomes empty (indicating a dead end).
        """
        peers = self._get_peers(row, col)
        for pr, pc in peers:
            # Only process unassigned cells
            if grid.get_cell(pr, pc).value is None:
                domains[(pr, pc)].discard(value)
                if not domains[(pr, pc)]:
                    return False
        return True

    def _find_hidden_single_in_unit(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        unit_cells: list[tuple[int, int]],
    ) -> Optional[tuple[int, int, int]]:
        """Find a hidden single in a unit (row, column, or box).

        A hidden single occurs when a value appears in exactly one
        unassigned cell's domain within a unit. That value must be
        assigned to that cell. (Requirement 5.5)

        Args:
            grid: The current grid state.
            domains: The current domain mapping.
            unit_cells: List of (row, col) tuples for cells in the unit.

        Returns:
            Tuple (row, col, value) if a hidden single is found, None otherwise.
        """
        # For each value 1-9, check if it appears in exactly one
        # unassigned cell's domain in this unit
        for value in range(1, 10):
            # Skip values already assigned in this unit
            assigned_in_unit = False
            for r, c in unit_cells:
                if grid.get_cell(r, c).value == value:
                    assigned_in_unit = True
                    break
            if assigned_in_unit:
                continue

            # Find unassigned cells that have this value in their domain
            candidates: list[tuple[int, int]] = []
            for r, c in unit_cells:
                if grid.get_cell(r, c).value is None and value in domains[(r, c)]:
                    candidates.append((r, c))

            # If exactly one cell can hold this value, it's a hidden single
            if len(candidates) == 1:
                hr, hc = candidates[0]
                return (hr, hc, value)

        return None

    def _propagate(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        states_explored: list[int],
        steps: Optional[list[StepEvent]],
        backtracks_count: list[int],
    ) -> bool:
        """Apply Naked Singles and Hidden Singles propagation to fixpoint.

        Repeatedly applies both propagation rules until no more changes occur:
        - Naked Singles (Req 5.4): cell domain reduced to 1 -> auto-assign
        - Hidden Singles (Req 5.5): value in exactly one cell's domain in a
          unit -> assign to that cell

        After each auto-assignment, forward checking is applied to propagate
        the constraint further.

        Args:
            grid: The current grid state (mutated by assignments).
            domains: The current domain mapping (mutated by propagation).
            states_explored: Single-element list used as mutable counter.
            steps: Optional list to collect StepEvents (for stepwise mode).
            backtracks_count: Single-element list for backtrack counter.

        Returns:
            True if propagation succeeded (no empty domains), False if a
            dead end was detected (some domain became empty).
        """
        changed = True
        while changed:
            changed = False

            # --- Naked Singles ---
            for r in range(9):
                for c in range(9):
                    if grid.get_cell(r, c).value is None and len(domains[(r, c)]) == 1:
                        value = next(iter(domains[(r, c)]))
                        grid.set_value(r, c, value)
                        states_explored[0] += 1
                        changed = True

                        if steps is not None:
                            steps.append(StepEvent(
                                step_type=StepType.ASSIGN,
                                row=r,
                                col=c,
                                value=value,
                                previous_value=None,
                                states_explored=states_explored[0],
                                backtracks=backtracks_count[0],
                            ))

                        if not self._forward_check(grid, domains, r, c, value):
                            return False

            # --- Hidden Singles (only if no naked singles found) ---
            if not changed:
                found_hidden = False

                # Check rows
                for r in range(9):
                    result = self._find_hidden_single_in_unit(
                        grid, domains, [(r, c) for c in range(9)]
                    )
                    if result is not None:
                        found_hidden = True
                        hr, hc, hval = result
                        grid.set_value(hr, hc, hval)
                        domains[(hr, hc)] = {hval}
                        states_explored[0] += 1
                        changed = True

                        if steps is not None:
                            steps.append(StepEvent(
                                step_type=StepType.ASSIGN,
                                row=hr,
                                col=hc,
                                value=hval,
                                previous_value=None,
                                states_explored=states_explored[0],
                                backtracks=backtracks_count[0],
                            ))

                        if not self._forward_check(grid, domains, hr, hc, hval):
                            return False
                        break

                if found_hidden:
                    continue

                # Check columns
                for c in range(9):
                    result = self._find_hidden_single_in_unit(
                        grid, domains, [(r, c) for r in range(9)]
                    )
                    if result is not None:
                        found_hidden = True
                        hr, hc, hval = result
                        grid.set_value(hr, hc, hval)
                        domains[(hr, hc)] = {hval}
                        states_explored[0] += 1
                        changed = True

                        if steps is not None:
                            steps.append(StepEvent(
                                step_type=StepType.ASSIGN,
                                row=hr,
                                col=hc,
                                value=hval,
                                previous_value=None,
                                states_explored=states_explored[0],
                                backtracks=backtracks_count[0],
                            ))

                        if not self._forward_check(grid, domains, hr, hc, hval):
                            return False
                        break

                if found_hidden:
                    continue

                # Check boxes
                for box in range(9):
                    box_r = (box // 3) * 3
                    box_c = (box % 3) * 3
                    box_cells = [
                        (box_r + dr, box_c + dc)
                        for dr in range(3) for dc in range(3)
                    ]
                    result = self._find_hidden_single_in_unit(
                        grid, domains, box_cells
                    )
                    if result is not None:
                        found_hidden = True
                        hr, hc, hval = result
                        grid.set_value(hr, hc, hval)
                        domains[(hr, hc)] = {hval}
                        states_explored[0] += 1
                        changed = True

                        if steps is not None:
                            steps.append(StepEvent(
                                step_type=StepType.ASSIGN,
                                row=hr,
                                col=hc,
                                value=hval,
                                previous_value=None,
                                states_explored=states_explored[0],
                                backtracks=backtracks_count[0],
                            ))

                        if not self._forward_check(grid, domains, hr, hc, hval):
                            return False
                        break

        return True

    def _select_mrv(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
    ) -> Optional[tuple[int, int]]:
        """Select the next variable using MRV heuristic.

        Chooses the unassigned cell with the fewest remaining values in its
        domain. Ties are broken by positional order (top-to-bottom,
        left-to-right). (Requirement 5.6)

        Args:
            grid: The current grid state.
            domains: The current domain mapping.

        Returns:
            Tuple (row, col) of the selected cell, or None if all cells
            are assigned.
        """
        best: Optional[tuple[int, int]] = None
        best_size = 10  # Larger than any possible domain

        for r in range(9):
            for c in range(9):
                if grid.get_cell(r, c).value is None:
                    size = len(domains[(r, c)])
                    if size < best_size:
                        best_size = size
                        best = (r, c)

        return best

    def _save_state(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
    ) -> tuple[list[list[Optional[int]]], dict[tuple[int, int], set[int]]]:
        """Save the current grid values and domains for backtracking.

        Creates deep copies of both the grid values and domain sets so
        they can be restored if the current path leads to a dead end.

        Args:
            grid: The current grid state.
            domains: The current domain mapping.

        Returns:
            Tuple of (grid_values, domains_copy) where grid_values is a
            9x9 list of Optional[int] and domains_copy is a deep copy
            of the domains dictionary.
        """
        grid_values = [
            [grid.get_cell(r, c).value for c in range(9)]
            for r in range(9)
        ]
        domains_copy = {k: set(v) for k, v in domains.items()}
        return grid_values, domains_copy

    def _restore_state(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        saved_values: list[list[Optional[int]]],
        saved_domains: dict[tuple[int, int], set[int]],
    ) -> None:
        """Restore grid values and domains from a saved state.

        Args:
            grid: The grid to restore (mutated in place).
            domains: The domains dict to restore (mutated in place).
            saved_values: Previously saved grid values.
            saved_domains: Previously saved domain sets.
        """
        for r in range(9):
            for c in range(9):
                val = saved_values[r][c]
                if val is None:
                    grid.clear_value(r, c)
                else:
                    grid.set_value(r, c, val)
        domains.clear()
        domains.update({k: set(v) for k, v in saved_domains.items()})

    def solve(self, grid: Grid, timeout: float = 60.0) -> SolveResult:
        """Solve the given Sudoku puzzle using Forward Checking with propagation.

        Works on a deep copy of the input grid to avoid mutating the original.
        Validates the initial grid for constraint violations before starting.
        If the grid is invalid, returns UNSOLVABLE immediately.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Returns:
            SolveResult containing:
                - SOLVED status with the completed grid if a solution is found.
                - UNSOLVABLE status if no solution exists or the grid is invalid.
                - TIMEOUT status with partial metrics if the timeout is exceeded.
        """
        start_time = time.monotonic()

        # Work on a copy to never mutate the original
        working_grid = grid.copy()

        # Validate initial grid for pre-existing constraint violations
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Initialize domains (Requirement 5.1)
        domains = self._initialize_domains(working_grid)

        # Check for empty domains in initial state (unsolvable)
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is None:
                    if not domains[(r, c)]:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(
                            solver_type=SolverType.FORWARD_CHECKING,
                            status=SolveStatus.UNSOLVABLE,
                            solved_grid=None,
                            time_ms=elapsed_ms,
                            states_explored=0,
                            backtracks=0,
                        )

        # Mutable counters passed by reference via single-element lists
        states_explored = [0]
        backtracks_count = [0]

        # Apply initial propagation
        if not self._propagate(
            working_grid, domains, states_explored, None, backtracks_count
        ):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )

        # Check if propagation alone solved the puzzle
        if working_grid.is_complete():
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )

        # Recursive search with backtracking
        result = self._search(
            working_grid, domains, states_explored, backtracks_count,
            start_time, timeout, None
        )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if result == "timeout":
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.TIMEOUT,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )
        elif result:
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )
        else:
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )

    def _search(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        states_explored: list[int],
        backtracks_count: list[int],
        start_time: float,
        timeout: float,
        steps: Optional[list[StepEvent]],
    ) -> object:
        """Recursive backtracking search with forward checking and propagation.

        Selects the next variable using MRV, tries each value in its domain,
        applies forward checking and propagation, and recurses. Backtracks
        on dead ends by restoring saved state.

        Args:
            grid: The working grid (mutated during search).
            domains: The domain mapping (mutated during search).
            states_explored: Mutable counter for states explored.
            backtracks_count: Mutable counter for backtracks.
            start_time: Monotonic start time for timeout checking.
            timeout: Maximum allowed seconds.
            steps: Optional list to collect StepEvents.

        Returns:
            True if solved, False if unsolvable, "timeout" if timed out.
        """
        # Check timeout
        if time.monotonic() - start_time >= timeout:
            return "timeout"

        # Check if puzzle is complete
        if grid.is_complete():
            return True

        # Select next variable using MRV (Requirement 5.6)
        cell = self._select_mrv(grid, domains)
        if cell is None:
            return True  # All assigned

        row, col = cell

        # If domain is empty, this is a dead end
        if not domains[(row, col)]:
            return False

        # Try each value in the domain
        values_to_try = sorted(domains[(row, col)])

        for value in values_to_try:
            # Check timeout periodically
            if time.monotonic() - start_time >= timeout:
                return "timeout"

            # Save state before assignment
            saved_values, saved_domains = self._save_state(grid, domains)

            # Assign value
            grid.set_value(row, col, value)
            domains[(row, col)] = {value}
            states_explored[0] += 1

            # Emit ASSIGN event
            if steps is not None:
                steps.append(StepEvent(
                    step_type=StepType.ASSIGN,
                    row=row,
                    col=col,
                    value=value,
                    previous_value=None,
                    states_explored=states_explored[0],
                    backtracks=backtracks_count[0],
                ))

            # Forward check: remove value from peer domains (Requirement 5.2)
            fc_ok = self._forward_check(grid, domains, row, col, value)

            if fc_ok:
                # Apply propagation (Naked Singles + Hidden Singles)
                prop_ok = self._propagate(
                    grid, domains, states_explored, steps, backtracks_count
                )

                if prop_ok:
                    # Recurse
                    result = self._search(
                        grid, domains, states_explored, backtracks_count,
                        start_time, timeout, steps
                    )
                    if result == "timeout":
                        return "timeout"
                    if result:
                        return True

            # Dead end - restore state and try next value
            self._restore_state(grid, domains, saved_values, saved_domains)
            backtracks_count[0] += 1

            # Emit BACKTRACK event
            if steps is not None:
                steps.append(StepEvent(
                    step_type=StepType.BACKTRACK,
                    row=row,
                    col=col,
                    value=None,
                    previous_value=value,
                    states_explored=states_explored[0],
                    backtracks=backtracks_count[0],
                ))

        # All values exhausted - backtrack (Requirement 5.8)
        return False

    def solve_stepwise(
        self, grid: Grid, timeout: float = 60.0
    ) -> Generator[StepEvent, None, SolveResult]:
        """Solve the puzzle yielding StepEvents for each state transition.

        This method implements the same algorithm as solve() but yields a
        StepEvent for each assignment and backtrack operation. This enables
        the UI to display step-by-step progress.

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Yields:
            StepEvent with step_type ASSIGN for value placements.
            StepEvent with step_type BACKTRACK for undone assignments.

        Returns:
            SolveResult upon completion.
        """
        start_time = time.monotonic()

        # Work on a copy to never mutate the original
        working_grid = grid.copy()

        # Validate initial grid
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Initialize domains
        domains = self._initialize_domains(working_grid)

        # Check for empty domains in initial state
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is None:
                    if not domains[(r, c)]:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(
                            solver_type=SolverType.FORWARD_CHECKING,
                            status=SolveStatus.UNSOLVABLE,
                            solved_grid=None,
                            time_ms=elapsed_ms,
                            states_explored=0,
                            backtracks=0,
                        )

        # Mutable counters
        states_explored = [0]
        backtracks_count = [0]

        # Collect steps in a list, then yield them
        collected_steps: list[StepEvent] = []

        # Apply initial propagation
        if not self._propagate(
            working_grid, domains, states_explored, collected_steps,
            backtracks_count
        ):
            # Yield any steps collected during propagation
            for step in collected_steps:
                yield step
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )

        # Yield initial propagation steps
        for step in collected_steps:
            yield step
        collected_steps.clear()

        # Check if propagation alone solved the puzzle
        if working_grid.is_complete():
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )

        # Recursive search collecting steps
        result = self._search(
            working_grid, domains, states_explored, backtracks_count,
            start_time, timeout, collected_steps
        )

        # Yield all collected steps from the search
        for step in collected_steps:
            yield step

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if result == "timeout":
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.TIMEOUT,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )
        elif result:
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )
        else:
            return SolveResult(
                solver_type=SolverType.FORWARD_CHECKING,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=states_explored[0],
                backtracks=backtracks_count[0],
            )
