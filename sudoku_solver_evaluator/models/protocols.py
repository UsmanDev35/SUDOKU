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
        # Abstract: solve the given grid and return a SolveResult.
        ...

    @abstractmethod
    def solve_stepwise(self, grid: Grid, timeout: float=60.0) -> Generator[StepEvent, None, SolveResult]:
        # Abstract: yield StepEvent objects while solving, then return SolveResult.
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        # Abstract: return a human-readable name for the solver/implementation.
        ...

class PuzzleGeneratorProtocol(ABC):

    @abstractmethod
    def generate(self, difficulty: DifficultyLevel, timeout: float=30.0) -> Grid:
        # Abstract: generate a puzzle at the requested difficulty within an optional timeout.
        ...

class PerformanceEvaluatorProtocol(ABC):

    @abstractmethod
    def record(self, result: SolveResult, puzzle_id: str, difficulty: DifficultyLevel) -> None:
        # Abstract: record a solve result for a puzzle and difficulty.
        ...

    @abstractmethod
    def get_comparison(self, puzzle_id: str) -> ComparisonTable:
        # Abstract: return a ComparisonTable for the given puzzle id.
        ...

    @abstractmethod
    def get_aggregate(self, difficulty: DifficultyLevel) -> AggregateStats:
        # Abstract: compute aggregate statistics for a difficulty level.
        ...

    @abstractmethod
    def export_csv(self, filepath: str) -> None:
        # Abstract: export recorded results to a CSV file.
        ...