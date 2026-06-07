import time
from collections import deque
from typing import Generator, Optional
from sudoku_solver_evaluator.constraints.validator import is_grid_valid
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol
_PEERS: dict[tuple[int, int], list[tuple[int, int]]] = {}
for _r in range(9):
    for _c in range(9):
        peers: set[tuple[int, int]] = set()
        for _cc in range(9):
            if _cc != _c:
                peers.add((_r, _cc))
        for _rr in range(9):
            if _rr != _r:
                peers.add((_rr, _c))
        _box_r = _r // 3 * 3
        _box_c = _c // 3 * 3
        for _rr in range(_box_r, _box_r + 3):
            for _cc in range(_box_c, _box_c + 3):
                if (_rr, _cc) != (_r, _c):
                    peers.add((_rr, _cc))
        _PEERS[_r, _c] = list(peers)

def _initialize_domains(grid: Grid) -> dict[tuple[int, int], set[int]]:
    domains: dict[tuple[int, int], set[int]] = {}
    for r in range(9):
        for c in range(9):
            cell = grid.get_cell(r, c)
            if cell.value is not None:
                domains[r, c] = {cell.value}
            else:
                domain = set(range(1, 10))
                for pr, pc in _PEERS[r, c]:
                    peer_val = grid.get_cell(pr, pc).value
                    if peer_val is not None:
                        domain.discard(peer_val)
                domains[r, c] = domain
    return domains

def _get_all_arcs() -> list[tuple[tuple[int, int], tuple[int, int]]]:
    arcs = []
    for cell, peers in _PEERS.items():
        for peer in peers:
            arcs.append((cell, peer))
    return arcs

def _get_affected_arcs(cell: tuple[int, int]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    arcs = []
    for peer in _PEERS[cell]:
        arcs.append((peer, cell))
    return arcs

def _ac3(domains: dict[tuple[int, int], set[int]], initial_arcs: Optional[list[tuple[tuple[int, int], tuple[int, int]]]]=None, propagation_events: Optional[list[tuple[int, int]]]=None) -> bool:
    if initial_arcs is None:
        queue = deque(_get_all_arcs())
    else:
        queue = deque(initial_arcs)
    while queue:
        xi, xj = queue.popleft()
        if _revise(domains, xi, xj):
            if propagation_events is not None:
                propagation_events.append(xi)
            if not domains[xi]:
                return False
            for peer in _PEERS[xi]:
                if peer != xj:
                    queue.append((peer, xi))
    return True

def _revise(domains: dict[tuple[int, int], set[int]], xi: tuple[int, int], xj: tuple[int, int]) -> bool:
    revised = False
    to_remove = []
    for v in domains[xi]:
        has_support = False
        for w in domains[xj]:
            if w != v:
                has_support = True
                break
        if not has_support:
            to_remove.append(v)
    for v in to_remove:
        domains[xi].discard(v)
        revised = True
    return revised

def _select_variable(domains: dict[tuple[int, int], set[int]], assigned: set[tuple[int, int]]) -> tuple[int, int]:
    best_cell: Optional[tuple[int, int]] = None
    best_domain_size = float('inf')
    best_degree = -1
    best_position = float('inf')
    for cell, domain in domains.items():
        if cell in assigned:
            continue
        domain_size = len(domain)
        if domain_size == 0:
            continue
        degree = sum((1 for peer in _PEERS[cell] if peer not in assigned))
        position = cell[0] * 9 + cell[1]
        if domain_size < best_domain_size or (domain_size == best_domain_size and degree > best_degree) or (domain_size == best_domain_size and degree == best_degree and (position < best_position)):
            best_cell = cell
            best_domain_size = domain_size
            best_degree = degree
            best_position = position
    assert best_cell is not None, 'No unassigned variable found'
    return best_cell

def _copy_domains(domains: dict[tuple[int, int], set[int]]) -> dict[tuple[int, int], set[int]]:
    return {cell: set(domain) for cell, domain in domains.items()}

class InformedSolver(SolverProtocol):

    def __init__(self) -> None:
        self._name = 'Informed Search (AC-3 + MRV)'

    @property
    def name(self) -> str:
        return self._name

    def solve(self, grid: Grid, timeout: float=60.0) -> SolveResult:
        start_time = time.monotonic()
        working_grid = grid.copy()
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        domains = _initialize_domains(working_grid)
        if not _ac3(domains):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        for cell, domain in domains.items():
            if not domain and working_grid.get_cell(cell[0], cell[1]).value is None:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        assigned: set[tuple[int, int]] = set()
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is not None:
                    assigned.add((r, c))
        self._assign_singletons(working_grid, domains, assigned)
        if len(assigned) == 81:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        metrics = [0, 0]
        result = self._backtrack(working_grid, domains, assigned, metrics, start_time, timeout)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        if result == 'timeout':
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.TIMEOUT, solved_grid=None, time_ms=elapsed_ms, states_explored=metrics[0], backtracks=metrics[1])
        elif result:
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=metrics[0], backtracks=metrics[1])
        else:
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=metrics[0], backtracks=metrics[1])

    def _assign_singletons(self, grid: Grid, domains: dict[tuple[int, int], set[int]], assigned: set[tuple[int, int]]) -> None:
        for cell, domain in domains.items():
            if cell not in assigned and len(domain) == 1:
                value = next(iter(domain))
                grid.set_value(cell[0], cell[1], value)
                assigned.add(cell)

    def _backtrack(self, grid: Grid, domains: dict[tuple[int, int], set[int]], assigned: set[tuple[int, int]], metrics: list[int], start_time: float, timeout: float) -> object:
        if time.monotonic() - start_time >= timeout:
            return 'timeout'
        if len(assigned) == 81:
            return True
        for cell, domain in domains.items():
            if cell not in assigned and (not domain):
                return False
        cell = _select_variable(domains, assigned)
        values_to_try = sorted(domains[cell])
        for value in values_to_try:
            if time.monotonic() - start_time >= timeout:
                return 'timeout'
            saved_domains = _copy_domains(domains)
            grid.set_value(cell[0], cell[1], value)
            domains[cell] = {value}
            assigned.add(cell)
            metrics[0] += 1
            affected_arcs = _get_affected_arcs(cell)
            consistent = _ac3(domains, affected_arcs)
            if consistent:
                wipeout = False
                for c, d in domains.items():
                    if c not in assigned and (not d):
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
                    result = self._backtrack(grid, domains, assigned, metrics, start_time, timeout)
                    if result == 'timeout':
                        return 'timeout'
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
        return False

    def solve_stepwise(self, grid: Grid, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        start_time = time.monotonic()
        working_grid = grid.copy()
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        domains = _initialize_domains(working_grid)
        if not _ac3(domains):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        for cell, domain in domains.items():
            if not domain and working_grid.get_cell(cell[0], cell[1]).value is None:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        assigned: set[tuple[int, int]] = set()
        for r in range(9):
            for c in range(9):
                if working_grid.get_cell(r, c).value is not None:
                    assigned.add((r, c))
        self._assign_singletons(working_grid, domains, assigned)
        if len(assigned) == 81:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        metrics = [0, 0]
        steps: list[StepEvent] = []
        result = self._backtrack_stepwise(working_grid, domains, assigned, metrics, steps, start_time, timeout)
        for step in steps:
            yield step
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        if result == 'timeout':
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.TIMEOUT, solved_grid=None, time_ms=elapsed_ms, states_explored=metrics[0], backtracks=metrics[1])
        elif result:
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=metrics[0], backtracks=metrics[1])
        else:
            return SolveResult(solver_type=SolverType.INFORMED, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=metrics[0], backtracks=metrics[1])

    def _backtrack_stepwise(self, grid: Grid, domains: dict[tuple[int, int], set[int]], assigned: set[tuple[int, int]], metrics: list[int], steps: list[StepEvent], start_time: float, timeout: float) -> object:
        if time.monotonic() - start_time >= timeout:
            return 'timeout'
        if len(assigned) == 81:
            return True
        for cell, domain in domains.items():
            if cell not in assigned and (not domain):
                return False
        cell = _select_variable(domains, assigned)
        values_to_try = sorted(domains[cell])
        for value in values_to_try:
            if time.monotonic() - start_time >= timeout:
                return 'timeout'
            saved_domains = _copy_domains(domains)
            grid.set_value(cell[0], cell[1], value)
            domains[cell] = {value}
            assigned.add(cell)
            metrics[0] += 1
            steps.append(StepEvent(step_type=StepType.ASSIGN, row=cell[0], col=cell[1], value=value, previous_value=None, states_explored=metrics[0], backtracks=metrics[1]))
            affected_arcs = _get_affected_arcs(cell)
            consistent = _ac3(domains, affected_arcs)
            if consistent:
                wipeout = False
                for c, d in domains.items():
                    if c not in assigned and (not d):
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
                    result = self._backtrack_stepwise(grid, domains, assigned, metrics, steps, start_time, timeout)
                    if result == 'timeout':
                        return 'timeout'
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
            steps.append(StepEvent(step_type=StepType.BACKTRACK, row=cell[0], col=cell[1], value=None, previous_value=value, states_explored=metrics[0], backtracks=metrics[1]))
        return False