import math
import random
import time
from typing import Generator, Optional
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol

class SimulatedAnnealingSolver(SolverProtocol):

    def __init__(self, initial_temp: float=1.0, cooling_rate: float=0.99, min_temp: float=0.001, max_restarts: int=10) -> None:
        self._initial_temp = initial_temp
        self._cooling_rate = cooling_rate
        self._min_temp = min_temp
        self._max_restarts = max_restarts

    @property
    def name(self) -> str:
        return 'Simulated Annealing'

    def _initialize_grid(self, grid: Grid) -> Grid:
        for box_index in range(9):
            box_cells = grid.get_box(box_index)
            fixed_values = set()
            non_fixed_cells = []
            for cell in box_cells:
                if cell.is_fixed:
                    fixed_values.add(cell.value)
                else:
                    non_fixed_cells.append(cell)
            missing_values = list(set(range(1, 10)) - fixed_values)
            random.shuffle(missing_values)
            for i, cell in enumerate(non_fixed_cells):
                grid.set_value(cell.row, cell.col, missing_values[i])
        return grid

    def _compute_cost(self, grid: Grid) -> int:
        cost = 0
        for row in range(9):
            value_counts: dict[int, int] = {}
            for col in range(9):
                val = grid.get_cell(row, col).value
                if val is not None:
                    value_counts[val] = value_counts.get(val, 0) + 1
            for count in value_counts.values():
                if count > 1:
                    cost += count - 1
        for col in range(9):
            value_counts = {}
            for row in range(9):
                val = grid.get_cell(row, col).value
                if val is not None:
                    value_counts[val] = value_counts.get(val, 0) + 1
            for count in value_counts.values():
                if count > 1:
                    cost += count - 1
        return cost

    def _compute_cost_delta(self, grid: Grid, row1: int, col1: int, row2: int, col2: int) -> int:
        val1 = grid.get_cell(row1, col1).value
        val2 = grid.get_cell(row2, col2).value
        if val1 == val2:
            return 0
        cost_before = 0
        cost_before += self._row_cost(grid, row1)
        cost_before += self._row_cost(grid, row2)
        cost_before += self._col_cost(grid, col1)
        cost_before += self._col_cost(grid, col2)
        if row1 == row2:
            cost_before -= self._row_cost(grid, row1)
        if col1 == col2:
            cost_before -= self._col_cost(grid, col1)
        grid.set_value(row1, col1, val2)
        grid.set_value(row2, col2, val1)
        cost_after = 0
        cost_after += self._row_cost(grid, row1)
        cost_after += self._row_cost(grid, row2)
        cost_after += self._col_cost(grid, col1)
        cost_after += self._col_cost(grid, col2)
        if row1 == row2:
            cost_after -= self._row_cost(grid, row1)
        if col1 == col2:
            cost_after -= self._col_cost(grid, col1)
        grid.set_value(row1, col1, val1)
        grid.set_value(row2, col2, val2)
        return cost_after - cost_before

    def _row_cost(self, grid: Grid, row: int) -> int:
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
        box_cells = grid.get_box(box_index)
        return [(cell.row, cell.col) for cell in box_cells if not cell.is_fixed]

    def solve(self, grid: Grid, timeout: float=60.0) -> SolveResult:
        start_time = time.monotonic()
        states_explored = 0
        restarts = 0
        best_cost: Optional[int] = None
        best_grid: Optional[Grid] = None
        working_grid = grid.copy()
        box_non_fixed: list[list[tuple[int, int]]] = []
        for box_index in range(9):
            box_non_fixed.append(self._get_non_fixed_cells_in_box(working_grid, box_index))
        swappable_boxes = [i for i in range(9) if len(box_non_fixed[i]) >= 2]
        if not swappable_boxes:
            working_grid = self._initialize_grid(working_grid)
            current_cost = self._compute_cost(working_grid)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            if current_cost == 0:
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, restarts=0, best_cost=0)
            else:
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.FAILED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, restarts=0, best_cost=current_cost)
        while restarts <= self._max_restarts:
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.TIMEOUT, solved_grid=best_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=best_cost)
            working_grid = grid.copy()
            self._initialize_grid(working_grid)
            current_cost = self._compute_cost(working_grid)
            if best_cost is None or current_cost < best_cost:
                best_cost = current_cost
                best_grid = working_grid.copy()
            if current_cost == 0:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=0)
            temperature = self._initial_temp
            while temperature >= self._min_temp:
                if time.monotonic() - start_time >= timeout:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.TIMEOUT, solved_grid=best_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=best_cost)
                box_index = random.choice(swappable_boxes)
                non_fixed = box_non_fixed[box_index]
                idx1, idx2 = random.sample(range(len(non_fixed)), 2)
                row1, col1 = non_fixed[idx1]
                row2, col2 = non_fixed[idx2]
                delta = self._compute_cost_delta(working_grid, row1, col1, row2, col2)
                states_explored += 1
                accept = False
                if delta <= 0:
                    accept = True
                else:
                    acceptance_probability = math.exp(-delta / temperature)
                    if random.random() < acceptance_probability:
                        accept = True
                if accept:
                    val1 = working_grid.get_cell(row1, col1).value
                    val2 = working_grid.get_cell(row2, col2).value
                    working_grid.set_value(row1, col1, val2)
                    working_grid.set_value(row2, col2, val1)
                    current_cost += delta
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_grid = working_grid.copy()
                    if current_cost == 0:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=0)
                temperature *= self._cooling_rate
            restarts += 1
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.FAILED, solved_grid=best_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=best_cost)

    def solve_stepwise(self, grid: Grid, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        start_time = time.monotonic()
        states_explored = 0
        restarts = 0
        best_cost: Optional[int] = None
        best_grid: Optional[Grid] = None
        working_grid = grid.copy()
        box_non_fixed: list[list[tuple[int, int]]] = []
        for box_index in range(9):
            box_non_fixed.append(self._get_non_fixed_cells_in_box(working_grid, box_index))
        swappable_boxes = [i for i in range(9) if len(box_non_fixed[i]) >= 2]
        if not swappable_boxes:
            working_grid = self._initialize_grid(working_grid)
            current_cost = self._compute_cost(working_grid)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            if current_cost == 0:
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, restarts=0, best_cost=0)
            else:
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.FAILED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, restarts=0, best_cost=current_cost)
        while restarts <= self._max_restarts:
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.TIMEOUT, solved_grid=best_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=best_cost)
            working_grid = grid.copy()
            self._initialize_grid(working_grid)
            current_cost = self._compute_cost(working_grid)
            if best_cost is None or current_cost < best_cost:
                best_cost = current_cost
                best_grid = working_grid.copy()
            if current_cost == 0:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=0)
            temperature = self._initial_temp
            while temperature >= self._min_temp:
                if time.monotonic() - start_time >= timeout:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.TIMEOUT, solved_grid=best_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=best_cost)
                box_index = random.choice(swappable_boxes)
                non_fixed = box_non_fixed[box_index]
                idx1, idx2 = random.sample(range(len(non_fixed)), 2)
                row1, col1 = non_fixed[idx1]
                row2, col2 = non_fixed[idx2]
                delta = self._compute_cost_delta(working_grid, row1, col1, row2, col2)
                states_explored += 1
                accept = False
                if delta <= 0:
                    accept = True
                else:
                    acceptance_probability = math.exp(-delta / temperature)
                    if random.random() < acceptance_probability:
                        accept = True
                if accept:
                    val1 = working_grid.get_cell(row1, col1).value
                    val2 = working_grid.get_cell(row2, col2).value
                    working_grid.set_value(row1, col1, val2)
                    working_grid.set_value(row2, col2, val1)
                    current_cost += delta
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_grid = working_grid.copy()
                    yield StepEvent(step_type=StepType.SWAP, row=row1, col=col1, value=val2, previous_value=val1, swap_row=row2, swap_col=col2, states_explored=states_explored, current_cost=current_cost)
                    if current_cost == 0:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=0)
                temperature *= self._cooling_rate
            restarts += 1
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return SolveResult(solver_type=SolverType.LOCAL_SEARCH, status=SolveStatus.FAILED, solved_grid=best_grid, time_ms=elapsed_ms, states_explored=states_explored, restarts=restarts, best_cost=best_cost)