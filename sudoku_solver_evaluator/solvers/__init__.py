from __future__ import annotations
from typing import Generator
from sudoku_solver_evaluator.models.enums import SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.models.protocols import SolverProtocol
from sudoku_solver_evaluator.solvers.backtracking import BacktrackingSolver
from sudoku_solver_evaluator.solvers.forward_checking import ForwardCheckingSolver
from sudoku_solver_evaluator.solvers.informed import InformedSolver
from sudoku_solver_evaluator.solvers.simulated_annealing import SimulatedAnnealingSolver

class SolverManager:

    def __init__(self) -> None:
        self._solvers: dict[SolverType, SolverProtocol] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(SolverType.BACKTRACKING, BacktrackingSolver())
        self.register(SolverType.INFORMED, InformedSolver())
        self.register(SolverType.LOCAL_SEARCH, SimulatedAnnealingSolver())
        self.register(SolverType.FORWARD_CHECKING, ForwardCheckingSolver())

    def register(self, solver_type: SolverType, solver: SolverProtocol) -> None:
        if not isinstance(solver, SolverProtocol):
            raise TypeError(f'Solver must implement SolverProtocol, got {type(solver).__name__}')
        self._solvers[solver_type] = solver

    def solve(self, grid: Grid, solver_type: SolverType, timeout: float=60.0) -> SolveResult:
        solver = self._get_solver(solver_type)
        return solver.solve(grid, timeout=timeout)

    def solve_all(self, grid: Grid, timeout: float=60.0) -> dict[SolverType, SolveResult]:
        results: dict[SolverType, SolveResult] = {}
        for solver_type, solver in self._solvers.items():
            results[solver_type] = solver.solve(grid, timeout=timeout)
        return results

    def solve_stepwise(self, grid: Grid, solver_type: SolverType, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        solver = self._get_solver(solver_type)
        return solver.solve_stepwise(grid, timeout=timeout)

    def _get_solver(self, solver_type: SolverType) -> SolverProtocol:
        if solver_type not in self._solvers:
            raise ValueError(f"No solver registered for type '{solver_type.value}'. Available types: {[t.value for t in self._solvers]}")
        return self._solvers[solver_type]

    @property
    def registered_solvers(self) -> dict[SolverType, SolverProtocol]:
        return dict(self._solvers)
__all__ = ['BacktrackingSolver', 'ForwardCheckingSolver', 'InformedSolver', 'SimulatedAnnealingSolver', 'SolverManager']