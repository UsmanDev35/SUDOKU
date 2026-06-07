import time
from typing import Generator, Optional
from sudoku_solver_evaluator.constraints.validator import is_grid_valid, is_valid_assignment
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol

class BacktrackingSolver(SolverProtocol):

    def __init__(self) -> None:
        self._name = 'Backtracking Search'

    @property
    def name(self) -> str:
        return self._name

    def solve(self, grid: Grid, timeout: float=60.0) -> SolveResult:
        start_time = time.monotonic()
        working_grid = grid.copy()
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        empty_cells = working_grid.get_empty_cells()
        if not empty_cells:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        states_explored = 0
        backtracks = 0
        cell_index = 0
        last_tried: list[int] = [0] * len(empty_cells)
        while 0 <= cell_index < len(empty_cells):
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.TIMEOUT, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored, backtracks=backtracks)
            cell = empty_cells[cell_index]
            row, col = (cell.row, cell.col)
            start_value = last_tried[cell_index] + 1
            found_valid = False
            for value in range(start_value, 10):
                if is_valid_assignment(working_grid, row, col, value):
                    working_grid.set_value(row, col, value)
                    last_tried[cell_index] = value
                    states_explored += 1
                    cell_index += 1
                    found_valid = True
                    break
            if not found_valid:
                working_grid.clear_value(row, col)
                last_tried[cell_index] = 0
                cell_index -= 1
                backtracks += 1
                if cell_index >= 0:
                    prev_cell = empty_cells[cell_index]
                    working_grid.clear_value(prev_cell.row, prev_cell.col)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        if cell_index == len(empty_cells):
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored, backtracks=backtracks)
        else:
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored, backtracks=backtracks)

    def solve_stepwise(self, grid: Grid, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        start_time = time.monotonic()
        working_grid = grid.copy()
        if not is_grid_valid(working_grid):
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        empty_cells = working_grid.get_empty_cells()
        if not empty_cells:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=0, backtracks=0)
        states_explored = 0
        backtracks = 0
        cell_index = 0
        last_tried: list[int] = [0] * len(empty_cells)
        while 0 <= cell_index < len(empty_cells):
            if time.monotonic() - start_time >= timeout:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.TIMEOUT, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored, backtracks=backtracks)
            cell = empty_cells[cell_index]
            row, col = (cell.row, cell.col)
            start_value = last_tried[cell_index] + 1
            found_valid = False
            for value in range(start_value, 10):
                if is_valid_assignment(working_grid, row, col, value):
                    working_grid.set_value(row, col, value)
                    last_tried[cell_index] = value
                    states_explored += 1
                    yield StepEvent(step_type=StepType.ASSIGN, row=row, col=col, value=value, previous_value=None, states_explored=states_explored, backtracks=backtracks)
                    cell_index += 1
                    found_valid = True
                    break
            if not found_valid:
                working_grid.clear_value(row, col)
                last_tried[cell_index] = 0
                cell_index -= 1
                backtracks += 1
                if cell_index >= 0:
                    prev_cell = empty_cells[cell_index]
                    previous_value = working_grid.get_cell(prev_cell.row, prev_cell.col).value
                    working_grid.clear_value(prev_cell.row, prev_cell.col)
                    yield StepEvent(step_type=StepType.BACKTRACK, row=prev_cell.row, col=prev_cell.col, value=None, previous_value=previous_value, states_explored=states_explored, backtracks=backtracks)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        if cell_index == len(empty_cells):
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.SOLVED, solved_grid=working_grid, time_ms=elapsed_ms, states_explored=states_explored, backtracks=backtracks)
        else:
            return SolveResult(solver_type=SolverType.BACKTRACKING, status=SolveStatus.UNSOLVABLE, solved_grid=None, time_ms=elapsed_ms, states_explored=states_explored, backtracks=backtracks)