import copy
import time
from typing import Generator, Optional
from sudoku_solver_evaluator.constraints.validator import is_grid_valid
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol

class ForwardCheckingSolver(SolverProtocol):

    def __init__(self) -> None:
        # Initialize solver display name.
        self._name = 'Forward Checking'

    @property
    def name(self) -> str:
        # Return the solver's display name.
        return self._name

    def _get_peers(self, row: int, col: int) -> list[tuple[int, int]]:
        # Return list of peer coordinates (row/col/box) for the given cell.
        peers: set[tuple[int, int]] = set()
        for c in range(9):
            if c != col:
                peers.add((row, c))
        for r in range(9):
            if r != row:
                peers.add((r, col))
        box_start_row = row // 3 * 3
        box_start_col = col // 3 * 3
        for r in range(box_start_row, box_start_row + 3):
            for c in range(box_start_col, box_start_col + 3):
                if (r, c) != (row, col):
                    peers.add((r, c))
        return list(peers)

    def _initialize_domains(self, grid: Grid) -> dict[tuple[int, int], set[int]]:
        # Initialize domains for each cell based on current assignments.
        domains: dict[tuple[int, int], set[int]] = {}
        for r in range(9):
            for c in range(9):
                cell = grid.get_cell(r, c)
                if cell.value is not None:
                    domains[r, c] = {cell.value}
                else:
                    domain = set(range(1, 10))
                    for cc in range(9):
                        val = grid.get_cell(r, cc).value
                        if val is not None:
                            domain.discard(val)
                    for rr in range(9):
                        val = grid.get_cell(rr, c).value
                        if val is not None:
                            domain.discard(val)
                    box_r = r // 3 * 3
                    box_c = c // 3 * 3
                    for rr in range(box_r, box_r + 3):
                        for cc in range(box_c, box_c + 3):
                            val = grid.get_cell(rr, cc).value
                            if val is not None:
                                domain.discard(val)
                    domains[r, c] = domain
        return domains

    def _forward_check(self, grid: Grid, domains: dict[tuple[int, int], set[int]], row: int, col: int, value: int) -> bool:
        # Remove `value` from peers' domains and return False if any domain empties.
        peers = self._get_peers(row, col)
        for pr, pc in peers:
            if grid.get_cell(pr, pc).value is None:
                domains[pr, pc].discard(value)
                if not domains[pr, pc]:
                    return False
        return True

    def _find_hidden_single_in_unit(self, grid: Grid, domains: dict[tuple[int, int], set[int]], unit_cells: list[tuple[int, int]]) -> Optional[tuple[int, int, int]]:
        # Find a hidden single in a unit; return its coordinates and value if found.
        for value in range(1, 10):
            assigned_in_unit = False
            for r, c in unit_cells:
                if grid.get_cell(r, c).value == value:
                    assigned_in_unit = True
                    break
            if assigned_in_unit:
                continue
            candidates: list[tuple[int, int]] = []
            for r, c in unit_cells:
                if grid.get_cell(r, c).value is None and value in domains[r, c]:
                    candidates.append((r, c))
            if len(candidates) == 1:
                hr, hc = candidates[0]
                return (hr, hc, value)
        return None

    def _propagate(self, grid: Grid, domains: dict[tuple[int, int], set[int]], states_explored: list[int], steps: Optional[list[StepEvent]], backtracks_count: list[int]) -> bool:
        # Propagate assignments and hidden singles until no further changes occur.
        changed = True
        while changed:
            changed = False
            for r in range(9):
                for c in range(9):
                    if grid.get_cell(r, c).value is None and len(domains[r, c]) == 1:
                        value = next(iter(domains[r, c]))
                        grid.set_value(r, c, value)
                        states_explored[0] += 1
                        changed = True
                        if steps is not None:
                            steps.append(StepEvent(step_type=StepType.ASSIGN, row=r, col=c, value=value, previous_value=None, states_explored=states_explored[0], backtracks=backtracks_count[0]))
                        if not self._forward_check(grid, domains, r, c, value):
                            return False
            if not changed:
                found_hidden = False
                for r in range(9):
                    result = self._find_hidden_single_in_unit(grid, domains, [(r, c) for c in range(9)])
                    if result is not None:
                        found_hidden = True
                        hr, hc, hval = result
                        grid.set_value(hr, hc, hval)
                        domains[hr, hc] = {hval}
                        states_explored[0] += 1
                        changed = True
                        if steps is not None:
                            steps.append(StepEvent(step_type=StepType.ASSIGN, row=hr, col=hc, value=hval, previous_value=None, states_explored=states_explored[0], backtracks=backtracks_count[0]))
                        if not self._forward_check(grid, domains, hr, hc, hval):
                            return False
                        break
                if found_hidden:
                    continue
                for c in range(9):
                    result = self._find_hidden_single_in_unit(grid, domains, [(r, c) for r in range(9)])
                    if result is not None:
                        found_hidden = True
                        hr, hc, hval = result
                        grid.set_value(hr, hc, hval)
                        domains[hr, hc] = {hval}
                        states_explored[0] += 1
                        changed = True
                        if steps is not None:
                            steps.append(StepEvent(step_type=StepType.ASSIGN, row=hr, col=hc, value=hval, previous_value=None, states_explored=states_explored[0], backtracks=backtracks_count[0]))
                        if not self._forward_check(grid, domains, hr, hc, hval):
                            return False
                        break
                if found_hidden:
                    continue
                for box in range(9):
                    box_r = box // 3 * 3
                    box_c = box % 3 * 3
                    box_cells = [(box_r + dr, box_c + dc) for dr in range(3) for dc in range(3)]
                    result = self._find_hidden_single_in_unit(grid, domains, box_cells)
                    if result is not None:
                        found_hidden = True
                        hr, hc, hval = result
                        grid.set_value(hr, hc, hval)
                        domains[hr, hc] = {hval}
                        states_explored[0] += 1
                        changed = True
                        if steps is not None:
                            steps.append(StepEvent(step_type=StepType.ASSIGN, row=hr, col=hc, value=hval, previous_value=None, states_explored=states_explored[0], backtracks=backtracks_count[0]))
                        if not self._forward_check(grid, domains, hr, hc, hval):
                            return False
                        break
        return True

    def _select_mrv(self, grid: Grid, domains: dict[tuple[int, int], set[int]]) -> Optional[tuple[int, int]]:
        # Select the unassigned variable with minimum remaining values (MRV heuristic).
        best: Optional[tuple[int, int]] = None
        best_size = 10
        for r in range(9):
            for c in range(9):
                if grid.get_cell(r, c).value is None:
                    size = len(domains[r, c])
                    if size < best_size:
                        best_size = size
                        best = (r, c)
        return best

    def _save_state(self, grid: Grid, domains: dict[tuple[int, int], set[int]]) -> tuple[list[list[Optional[int]]], dict[tuple[int, int], set[int]]]:
        # Save a lightweight snapshot of grid values and domains for backtracking.
        grid_values = [[grid.get_cell(r, c).value for c in range(9)] for r in range(9)]
        domains_copy = {k: set(v) for k, v in domains.items()}
        return (grid_values, domains_copy)

    def _restore_state(self, grid: Grid, domains: dict[tuple[int, int], set[int]], saved_values: list[list[Optional[int]]], saved_domains: dict[tuple[int, int], set[int]]) -> None:
        # Restore a previously saved snapshot of values and domains.
        for r in range(9):
            for c in range(9):
                val = saved_values[r][c]
                if val is None:
                    grid.clear_value(r, c)
                else:
                    grid.set_value(r, c, val)
        domains.clear()
        domains.update({k: set(v) for k, v in saved_domains.items()})

    def solve(self, grid: Grid, timeout: float=60.0) -> SolveResult:
        # Solve using forward checking with propagation and MRV-guided search.
        start_time = time.monotonic()
        working_grid = grid.copy()
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        domains = self._initialize_domains(working_grid)
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is None:
                    if not domains[r, c]:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        states_explored = [0]
        backtracks_count = [0]
        if not self._propagate(working_grid, domains, states_explored, None, backtracks_count):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        if working_grid.is_complete():
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        result = self._search(working_grid, domains, states_explored, backtracks_count, start_time, timeout, None)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        if result == 'timeout':
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.TIMEOUT, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        elif result:
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        else:
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])

    def _search(self, grid: Grid, domains: dict[tuple[int, int], set[int]], states_explored: list[int], backtracks_count: list[int], start_time: float, timeout: float, steps: Optional[list[StepEvent]]) -> object:
        # Recursive search using forward checking, propagation, and backtracking.
        if time.monotonic() - start_time >= timeout:
            return 'timeout'
        if grid.is_complete():
            return True
        cell = self._select_mrv(grid, domains)
        if cell is None:
            return True
        row, col = cell
        if not domains[row, col]:
            return False
        values_to_try = sorted(domains[row, col])
        for value in values_to_try:
            if time.monotonic() - start_time >= timeout:
                return 'timeout'
            saved_values, saved_domains = self._save_state(grid, domains)
            grid.set_value(row, col, value)
            domains[row, col] = {value}
            states_explored[0] += 1
            if steps is not None:
                steps.append(StepEvent(step_type=StepType.ASSIGN, row=row, col=col, value=value, previous_value=None, states_explored=states_explored[0], backtracks=backtracks_count[0]))
            fc_ok = self._forward_check(grid, domains, row, col, value)
            if fc_ok:
                prop_ok = self._propagate(grid, domains, states_explored, steps, backtracks_count)
                if prop_ok:
                    result = self._search(grid, domains, states_explored, backtracks_count, start_time, timeout, steps)
                    if result == 'timeout':
                        return 'timeout'
                    if result:
                        return True
            self._restore_state(grid, domains, saved_values, saved_domains)
            backtracks_count[0] += 1
            if steps is not None:
                steps.append(StepEvent(step_type=StepType.BACKTRACK, row=row, col=col, value=None, previous_value=value, states_explored=states_explored[0], backtracks=backtracks_count[0]))
        return False

    def solve_stepwise(self, grid: Grid, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        # Solve while yielding step events for visualization of propagation and decisions.
        start_time = time.monotonic()
        working_grid = grid.copy()
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        domains = self._initialize_domains(working_grid)
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is None:
                    if not domains[r, c]:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        states_explored = [0]
        backtracks_count = [0]
        collected_steps: list[StepEvent] = []
        if not self._propagate(working_grid, domains, states_explored, collected_steps, backtracks_count):
            for step in collected_steps:
                yield step
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        for step in collected_steps:
            yield step
        collected_steps.clear()
        if working_grid.is_complete():
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        result = self._search(working_grid, domains, states_explored, backtracks_count, start_time, timeout, collected_steps)
        for step in collected_steps:
            yield step
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        if result == 'timeout':
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.TIMEOUT, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        elif result:
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])
        else:
            return SolveResult(solver_type=SolverType.FORWARD_CHECKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored[0], backtracks=backtracks_count[0])