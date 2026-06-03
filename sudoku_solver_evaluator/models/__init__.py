"""Data models for the Sudoku Solver and Evaluator system.

Contains Grid/Cell structures, enumerations, metrics dataclasses,
and abstract protocol definitions.
"""

from sudoku_solver_evaluator.models.enums import (
    DifficultyLevel,
    SolveStatus,
    SolverType,
    StepType,
)
from sudoku_solver_evaluator.models.metrics import (
    AggregateStats,
    AlgorithmStats,
    ComparisonTable,
    RaceResult,
    RaceStatus,
    SolveResult,
    StepEvent,
)
from sudoku_solver_evaluator.models.grid import Cell, Grid
from sudoku_solver_evaluator.models.protocols import (
    PerformanceEvaluatorProtocol,
    PuzzleGeneratorProtocol,
    SolverProtocol,
)

__all__ = [
    # Grid and Cell
    "Cell",
    "Grid",
    # Enumerations
    "DifficultyLevel",
    "SolveStatus",
    "SolverType",
    "StepType",
    # Metrics and Results
    "AggregateStats",
    "AlgorithmStats",
    "ComparisonTable",
    "RaceResult",
    "RaceStatus",
    "SolveResult",
    "StepEvent",
    # Protocols / Abstract Interfaces
    "SolverProtocol",
    "PuzzleGeneratorProtocol",
    "PerformanceEvaluatorProtocol",
]
