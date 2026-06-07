"""Informed Search solver using AC-3 + MRV + Degree Heuristic.

This module implements an informed constraint-satisfaction solver for Sudoku
puzzles. It combines three key techniques:

1. **AC-3 (Arc Consistency Algorithm #3)**: Enforces arc consistency by
   iteratively removing values from variable domains that have no support
   in neighboring variables. This prunes the search space before and during
   backtracking search.

2. **MRV (Minimum Remaining Values) Heuristic**: Selects the unassigned
   variable with the smallest domain (fewest legal values remaining). This
   "fail-first" strategy detects dead ends early.

3. **Degree Heuristic**: Breaks MRV ties by selecting the variable involved
   in the most constraints with other unassigned variables. This maximizes
   constraint propagation from each assignment.

Algorithm Overview:
    1. Work on a copy of the input grid.
    2. Validate initial grid (return UNSOLVABLE if invalid).
    3. Initialize domains for all empty cells (values 1-9 minus peer values).
    4. Run AC-3 on all arcs to enforce initial arc consistency.
    5. If any domain becomes empty during initial AC-3, return UNSOLVABLE.
    6. Begin recursive backtracking search:
       a. If all cells assigned, return SOLVED.
       b. Select next variable using MRV, Degree Heuristic, then positional order.
       c. For each value in the selected cell's domain:
          - Save domain state for backtracking.
          - Assign value, set domain to {value}.
          - Run AC-3 on arcs affected by this assignment.
          - If no domain becomes empty, recurse.
          - If domain becomes empty or recursion fails, restore domains.
       d. If no value works, backtrack.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

import time
from collections import deque
from typing import Generator, Optional

from sudoku_solver_evaluator.constraints.validator import is_grid_valid
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol


# Pre-compute peer relationships for all 81 cells.
# Each cell's peers are the set of cells in the same row, column, or box
# (excluding itself). This is computed once and reused across all solve calls.
_PEERS: dict[tuple[int, int], list[tuple[int, int]]] = {}

for _r in range(9):
    for _c in range(9):
        peers: set[tuple[int, int]] = set()
        # Same row
        for _cc in range(9):
            if _cc != _c:
                peers.add((_r, _cc))
        # Same column
        for _rr in range(9):
            if _rr != _r:
                peers.add((_rr, _c))
        # Same 3x3 box
        _box_r = (_r // 3) * 3
        _box_c = (_c // 3) * 3
        for _rr in range(_box_r, _box_r + 3):
            for _cc in range(_box_c, _box_c + 3):
                if (_rr, _cc) != (_r, _c):
                    peers.add((_rr, _cc))
        _PEERS[(_r, _c)] = list(peers)


def _initialize_domains(grid: Grid) -> dict[tuple[int, int], set[int]]:
    """Initialize domains for all cells based on current grid state.

    For each empty cell, the domain starts as {1..9} minus any values
    already assigned to peers (cells in the same row, column, or box).
    For assigned cells, the domain is {value}.

    Args:
        grid: The current Sudoku grid.

    Returns:
        A dictionary mapping (row, col) to the set of possible values.
    """
    domains: dict[tuple[int, int], set[int]] = {}

    for r in range(9):
        for c in range(9):
            cell = grid.get_cell(r, c)
            if cell.value is not None:
                # Assigned cells have a singleton domain
                domains[(r, c)] = {cell.value}
            else:
                # Start with all values, then remove those in peers
                domain = set(range(1, 10))
                for pr, pc in _PEERS[(r, c)]:
                    peer_val = grid.get_cell(pr, pc).value
                    if peer_val is not None:
                        domain.discard(peer_val)
                domains[(r, c)] = domain

    return domains


def _get_all_arcs() -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Get all constraint arcs in the Sudoku CSP.

    An arc (Xi, Xj) represents a constraint between two cells where
    Xi and Xj are peers (same row, column, or box). For arc consistency,
    every value in Xi's domain must have at least one consistent value
    in Xj's domain.

    Returns:
        A list of all (cell_i, cell_j) arcs where cell_i and cell_j are peers.
    """
    arcs = []
    for cell, peers in _PEERS.items():
        for peer in peers:
            arcs.append((cell, peer))
    return arcs


def _get_affected_arcs(
    cell: tuple[int, int],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Get arcs affected by an assignment to the given cell.

    When a value is assigned to a cell, we need to re-check arc consistency
    for all arcs (Xk, cell) where Xk is a peer of the assigned cell.
    This is because the assigned cell's domain changed, which may affect
    whether peers' values have support.

    Args:
        cell: The (row, col) of the cell that was just assigned.

    Returns:
        List of arcs (peer, cell) for all peers of the given cell.
    """
    arcs = []
    for peer in _PEERS[cell]:
        arcs.append((peer, cell))
    return arcs


def _ac3(
    domains: dict[tuple[int, int], set[int]],
    initial_arcs: Optional[list[tuple[tuple[int, int], tuple[int, int]]]] = None,
    propagation_events: Optional[list[tuple[int, int]]] = None,
) -> bool:
    """Enforce arc consistency using the AC-3 algorithm.

    AC-3 works by maintaining a queue of arcs to process. For each arc
    (Xi, Xj), it checks whether every value in Xi's domain has at least
    one consistent (different) value in Xj's domain. If not, that value
    is removed from Xi's domain. When Xi's domain changes, all arcs
    (Xk, Xi) are re-added to the queue (except the arc that triggered
    the change).

    The algorithm terminates when:
    - The queue is empty (arc consistency achieved), or
    - Some domain becomes empty (inconsistency detected).

    Args:
        domains: Mutable dictionary of (row, col) -> set of possible values.
            Modified in place as values are pruned.
        initial_arcs: The initial set of arcs to process. If None, all arcs
            in the CSP are used (for initial enforcement).
        propagation_events: Optional list to collect (row, col) of cells
            whose domains were reduced. Used by solve_stepwise to emit
            PROPAGATE StepEvents.

    Returns:
        True if arc consistency was achieved (no empty domains).
        False if any domain was reduced to empty (inconsistency).
    """
    # Initialize the queue with all arcs or the provided subset
    if initial_arcs is None:
        queue = deque(_get_all_arcs())
    else:
        queue = deque(initial_arcs)

    while queue:
        xi, xj = queue.popleft()

        # Revise: remove values from Xi's domain that have no support in Xj
        if _revise(domains, xi, xj):
            # Xi's domain was reduced
            if propagation_events is not None:
                propagation_events.append(xi)

            if not domains[xi]:
                # Domain wiped out - inconsistency detected
                return False

            # Add all arcs (Xk, Xi) where Xk is a peer of Xi, except Xj
            # because we just processed (Xi, Xj) and Xj's domain didn't change
            for peer in _PEERS[xi]:
                if peer != xj:
                    queue.append((peer, xi))

    return True


def _revise(
    domains: dict[tuple[int, int], set[int]],
    xi: tuple[int, int],
    xj: tuple[int, int],
) -> bool:
    """Revise the domain of Xi with respect to Xj.

    For the Sudoku all-different constraint, a value v in Xi's domain
    is unsupported if Xj's domain is exactly {v} (meaning Xj must take
    that value, so Xi cannot). More precisely, v has support in Xj if
    there exists at least one value w in Xj's domain such that w != v.

    Args:
        domains: The current domain mapping.
        xi: The cell whose domain may be reduced.
        xj: The constraining peer cell.

    Returns:
        True if at least one value was removed from Xi's domain.
    """
    revised = False
    # We need to iterate over a copy since we may modify the set
    to_remove = []

    for v in domains[xi]:
        # Check if there's any value in Xj's domain that is different from v
        # For Sudoku's all-different constraint: v is supported if Xj has
        # at least one value != v
        has_support = False
        for w in domains[xj]:
            if w != v:
                has_support = True
                break

        if not has_support:
            # v has no support in Xj - must remove it from Xi's domain
            to_remove.append(v)

    for v in to_remove:
        domains[xi].discard(v)
        revised = True

    return revised


def _select_variable(
    domains: dict[tuple[int, int], set[int]],
    assigned: set[tuple[int, int]],
) -> tuple[int, int]:
    """Select the next unassigned variable using MRV + Degree Heuristic.

    Variable selection strategy (Requirement 3.2, 3.3):
    1. **MRV (Minimum Remaining Values)**: Choose the unassigned cell with
       the smallest domain size. This "fail-first" approach detects dead
       ends early in the search.
    2. **Degree Heuristic** (tie-breaker): Among cells with the same minimum
       domain size, choose the one with the most constraints involving other
       unassigned cells. This maximizes propagation from the assignment.
    3. **Positional Order** (final tie-breaker): Among still-tied cells,
       choose by row*9+col in ascending order (left-to-right, top-to-bottom).

    Args:
        domains: Current domain mapping for all cells.
        assigned: Set of (row, col) tuples for cells already assigned.

    Returns:
        The (row, col) of the selected variable.
    """
    best_cell: Optional[tuple[int, int]] = None
    best_domain_size = float("inf")
    best_degree = -1
    best_position = float("inf")

    for cell, domain in domains.items():
        if cell in assigned:
            continue

        domain_size = len(domain)
        if domain_size == 0:
            # Skip cells with empty domains (shouldn't happen in valid state)
            continue

        # Count unassigned peers (degree heuristic)
        degree = sum(1 for peer in _PEERS[cell] if peer not in assigned)

        # Positional order: row * 9 + col
        position = cell[0] * 9 + cell[1]

        # Compare using MRV first, then Degree (higher is better), then position
        if (
            domain_size < best_domain_size
            or (domain_size == best_domain_size and degree > best_degree)
            or (
                domain_size == best_domain_size
                and degree == best_degree
                and position < best_position
            )
        ):
            best_cell = cell
            best_domain_size = domain_size
            best_degree = degree
            best_position = position

    assert best_cell is not None, "No unassigned variable found"
    return best_cell


def _copy_domains(
    domains: dict[tuple[int, int], set[int]],
) -> dict[tuple[int, int], set[int]]:
    """Create a deep copy of the domains dictionary.

    Each domain set is copied independently so modifications to the copy
    do not affect the original.

    Args:
        domains: The domain mapping to copy.

    Returns:
        A new dictionary with independent set copies for each cell.
    """
    return {cell: set(domain) for cell, domain in domains.items()}


class InformedSolver(SolverProtocol):
    """Informed Search solver using AC-3 + MRV + Degree Heuristic.

    This solver combines arc consistency enforcement with intelligent variable
    selection heuristics to efficiently solve Sudoku puzzles. The AC-3 algorithm
    prunes impossible values from cell domains, while MRV and Degree Heuristic
    guide the search toward the most constrained variables first.

    Compared to the basic backtracking solver, this approach typically explores
    far fewer states because:
    - AC-3 eliminates values that cannot lead to solutions
    - MRV detects dead ends early by choosing the most constrained variable
    - Degree Heuristic maximizes constraint propagation from each assignment

    Attributes:
        _name: Human-readable name identifying this solver.
    """

    def __init__(self) -> None:
        """Initialize the InformedSolver."""
        self._name = "Informed Search (AC-3 + MRV)"

    @property
    def name(self) -> str:
        """Human-readable name of the solver.

        Returns:
            The string 'Informed Search (AC-3 + MRV)'.
        """
        return self._name

    def solve(self, grid: Grid, timeout: float = 60.0) -> SolveResult:
        """Solve the given Sudoku puzzle using AC-3 + MRV + Degree Heuristic.

        Works on a deep copy of the input grid to avoid mutating the original.
        Validates the initial grid for constraint violations before starting.
        Uses recursive backtracking with AC-3 propagation after each assignment.

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

        # Work on a copy to never mutate the original (Requirement 3.8)
        working_grid = grid.copy()

        # Validate initial grid for pre-existing constraint violations
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Initialize domains for all cells (Requirement 3.1)
        domains = _initialize_domains(working_grid)

        # Run AC-3 on all arcs to enforce initial arc consistency (Requirement 3.1)
        if not _ac3(domains):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Check if any domain is empty after initial AC-3
        for cell, domain in domains.items():
            if not domain and working_grid.get_cell(cell[0], cell[1]).value is None:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.INFORMED,
                    status=SolveStatus.UNSOLVABLE,
                    solved_grid=None,
                    time_ms=elapsed_ms,
                    states_explored=0,
                    backtracks=0,
                )

        # Build the set of already-assigned cells
        assigned: set[tuple[int, int]] = set()
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is not None:
                    assigned.add((r, c))

        # Auto-assign all singleton domains from initial AC-3
        self._assign_singletons(working_grid, domains, assigned)

        # If all cells are already assigned, puzzle is solved
        if len(assigned) == 81:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Metrics counters
        metrics = [0, 0]  # [states_explored, backtracks]

        # Recursive backtracking search
        result = self._backtrack(
            working_grid, domains, assigned, metrics, start_time, timeout
        )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if result == "timeout":
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.TIMEOUT,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=metrics[0],
                backtracks=metrics[1],
            )
        elif result:
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=metrics[0],
                backtracks=metrics[1],
            )
        else:
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=metrics[0],
                backtracks=metrics[1],
            )

    def _assign_singletons(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        assigned: set[tuple[int, int]],
    ) -> None:
        """Auto-assign all cells with singleton domains (forced by AC-3)."""
        for cell, domain in domains.items():
            if cell not in assigned and len(domain) == 1:
                value = next(iter(domain))
                grid.set_value(cell[0], cell[1], value)
                assigned.add(cell)

    def _backtrack(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        assigned: set[tuple[int, int]],
        metrics: list[int],
        start_time: float,
        timeout: float,
    ) -> object:
        """Recursive backtracking with AC-3 propagation.

        Returns True if solved, False if unsolvable, "timeout" if timed out.
        """
        # Check timeout
        if time.monotonic() - start_time >= timeout:
            return "timeout"

        # Check if complete
        if len(assigned) == 81:
            return True

        # Check for any empty domain among unassigned cells
        for cell, domain in domains.items():
            if cell not in assigned and not domain:
                return False

        # Select next variable using MRV + Degree (Requirement 3.2, 3.3)
        cell = _select_variable(domains, assigned)
        values_to_try = sorted(domains[cell])

        for value in values_to_try:
            # Check timeout
            if time.monotonic() - start_time >= timeout:
                return "timeout"

            # Save state before assignment
            saved_domains = _copy_domains(domains)

            # Assign value
            grid.set_value(cell[0], cell[1], value)
            domains[cell] = {value}
            assigned.add(cell)
            metrics[0] += 1  # states_explored

            # Run AC-3 on affected arcs (Requirement 3.4)
            affected_arcs = _get_affected_arcs(cell)
            consistent = _ac3(domains, affected_arcs)

            if consistent:
                # Check for domain wipeout
                wipeout = False
                for c, d in domains.items():
                    if c not in assigned and not d:
                        wipeout = True
                        break

                if not wipeout:
                    # Auto-assign any new singletons created by propagation
                    new_singletons = []
                    for c, d in domains.items():
                        if c not in assigned and len(d) == 1:
                            new_singletons.append((c, next(iter(d))))

                    for (sr, sc), sv in new_singletons:
                        grid.set_value(sr, sc, sv)
                        assigned.add((sr, sc))

                    # Recurse
                    result = self._backtrack(
                        grid, domains, assigned, metrics, start_time, timeout
                    )
                    if result == "timeout":
                        return "timeout"
                    if result:
                        return True

                    # Undo singleton assignments
                    for (sr, sc), _ in new_singletons:
                        grid.clear_value(sr, sc)
                        assigned.discard((sr, sc))

            # Restore state (Requirement 3.5)
            domains.clear()
            domains.update(saved_domains)
            grid.clear_value(cell[0], cell[1])
            assigned.discard(cell)
            metrics[1] += 1  # backtracks

        return False

    def solve_stepwise(
        self, grid: Grid, timeout: float = 60.0
    ) -> Generator[StepEvent, None, SolveResult]:
        """Solve the puzzle yielding StepEvents for each state transition.

        Same algorithm as solve() but yields StepEvent for:
        - ASSIGN events when a value is placed
        - BACKTRACK events when a value is undone

        Args:
            grid: The initial puzzle grid (not mutated).
            timeout: Maximum wall-clock seconds allowed. Defaults to 60.0.

        Yields:
            StepEvent with step_type ASSIGN or BACKTRACK.

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
                solver_type=SolverType.INFORMED,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Initialize domains
        domains = _initialize_domains(working_grid)

        # Run AC-3 on all arcs for initial arc consistency
        if not _ac3(domains):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Check for empty domains after initial AC-3
        for cell, domain in domains.items():
            if not domain and working_grid.get_cell(cell[0], cell[1]).value is None:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(
                    solver_type=SolverType.INFORMED,
                    status=SolveStatus.UNSOLVABLE,
                    solved_grid=None,
                    time_ms=elapsed_ms,
                    states_explored=0,
                    backtracks=0,
                )

        # Build assigned set
        assigned: set[tuple[int, int]] = set()
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is not None:
                    assigned.add((r, c))

        # Auto-assign singletons from initial AC-3
        self._assign_singletons(working_grid, domains, assigned)

        # If already complete
        if len(assigned) == 81:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=0,
                backtracks=0,
            )

        # Metrics
        metrics = [0, 0]  # [states_explored, backtracks]
        steps: list[StepEvent] = []

        # Recursive solve collecting steps
        result = self._backtrack_stepwise(
            working_grid, domains, assigned, metrics, steps, start_time, timeout
        )

        # Yield all collected steps
        for step in steps:
            yield step

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if result == "timeout":
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.TIMEOUT,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=metrics[0],
                backtracks=metrics[1],
            )
        elif result:
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.SOLVED,
                solved_grid=working_grid,
                time_ms=elapsed_ms,
                states_explored=metrics[0],
                backtracks=metrics[1],
            )
        else:
            return SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.UNSOLVABLE,
                solved_grid=None,
                time_ms=elapsed_ms,
                states_explored=metrics[0],
                backtracks=metrics[1],
            )

    def _backtrack_stepwise(
        self,
        grid: Grid,
        domains: dict[tuple[int, int], set[int]],
        assigned: set[tuple[int, int]],
        metrics: list[int],
        steps: list[StepEvent],
        start_time: float,
        timeout: float,
    ) -> object:
        """Recursive backtracking with step event collection."""
        if time.monotonic() - start_time >= timeout:
            return "timeout"

        if len(assigned) == 81:
            return True

        for cell, domain in domains.items():
            if cell not in assigned and not domain:
                return False

        cell = _select_variable(domains, assigned)
        values_to_try = sorted(domains[cell])

        for value in values_to_try:
            if time.monotonic() - start_time >= timeout:
                return "timeout"

            saved_domains = _copy_domains(domains)

            grid.set_value(cell[0], cell[1], value)
            domains[cell] = {value}
            assigned.add(cell)
            metrics[0] += 1

            steps.append(StepEvent(
                step_type=StepType.ASSIGN,
                row=cell[0],
                col=cell[1],
                value=value,
                previous_value=None,
                states_explored=metrics[0],
                backtracks=metrics[1],
            ))

            affected_arcs = _get_affected_arcs(cell)
            consistent = _ac3(domains, affected_arcs)

            if consistent:
                wipeout = False
                for c, d in domains.items():
                    if c not in assigned and not d:
                        wipeout = True
                        break

                if not wipeout:
                    new_singletons = []
                    for c, d in domains.items():
                        if c not in assigned and len(d) == 1:
                            new_singletons.append((c, next(iter(d))))

                    for (sr, sc), sv in new_singletons:
                        grid.set_value(sr, sc, sv)
                        assigned.add((sr, sc))

                    result = self._backtrack_stepwise(
                        grid, domains, assigned, metrics, steps, start_time, timeout
                    )
                    if result == "timeout":
                        return "timeout"
                    if result:
                        return True

                    for (sr, sc), _ in new_singletons:
                        grid.clear_value(sr, sc)
                        assigned.discard((sr, sc))

            domains.clear()
            domains.update(saved_domains)
            grid.clear_value(cell[0], cell[1])
            assigned.discard(cell)
            metrics[1] += 1

            steps.append(StepEvent(
                step_type=StepType.BACKTRACK,
                row=cell[0],
                col=cell[1],
                value=None,
                previous_value=value,
                states_explored=metrics[0],
                backtracks=metrics[1],
            ))

        return False
