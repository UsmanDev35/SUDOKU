from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generator
if TYPE_CHECKING:
    from sudoku_solver_evaluator.models.enums import DifficultyLevel
    from sudoku_solver_evaluator.models.grid import Grid
    from sudoku_solver_evaluator.models.metrics import AggregateStats, ComparisonTable, SolveResult, StepEvent

class SolverProtocol(ABC):

    @abstractmethod
    def solve(self, grid: Grid, timeout: float=60.0) -> SolveResult:
        ...

    @abstractmethod
    def solve_stepwise(self, grid: Grid, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

class PuzzleGeneratorProtocol(ABC):

    @abstractmethod
    def generate(self, difficulty: DifficultyLevel, timeout: float=30.0) -> Grid:
        ...

class PerformanceEvaluatorProtocol(ABC):

    @abstractmethod
    def record(self, result: SolveResult, puzzle_id: str, difficulty: DifficultyLevel) -> None:
        ...

    @abstractmethod
    def get_comparison(self, puzzle_id: str) -> ComparisonTable:
        ...

    @abstractmethod
    def get_aggregate(self, difficulty: DifficultyLevel) -> AggregateStats:
        ...

    @abstractmethod
    def export_csv(self, filepath: str) -> None:
        ...