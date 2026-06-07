from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType, StepType
if TYPE_CHECKING:
    from sudoku_solver_evaluator.models.grid import Grid

@dataclass
class SolveResult:
    solver_type: SolverType
    status: SolveStatus
    solved_grid: Optional['Grid'] = None
    time_ms: int = 0
    states_explored: int = 0
    backtracks: int = 0
    restarts: int = 0
    best_cost: Optional[int] = None

@dataclass
class StepEvent:
    step_type: StepType
    row: int
    col: int
    value: Optional[int] = None
    previous_value: Optional[int] = None
    swap_row: Optional[int] = None
    swap_col: Optional[int] = None
    states_explored: int = 0
    backtracks: int = 0
    current_cost: Optional[int] = None

@dataclass
class ComparisonTable:
    puzzle_id: str
    difficulty: DifficultyLevel
    results: dict[SolverType, SolveResult] = field(default_factory=dict)
    rankings: dict[str, list[SolverType]] = field(default_factory=dict)

@dataclass
class AlgorithmStats:
    mean_time_ms: float
    min_time_ms: int
    max_time_ms: int
    mean_states: float
    min_states: int
    max_states: int
    mean_backtracks: float
    min_backtracks: int
    max_backtracks: int
    solve_rate: float

@dataclass
class AggregateStats:
    difficulty: DifficultyLevel
    puzzle_count: int
    stats: dict[SolverType, AlgorithmStats] = field(default_factory=dict)

@dataclass
class RaceResult:
    solver_a_type: SolverType
    solver_b_type: SolverType
    solver_a_result: SolveResult
    solver_b_result: SolveResult
    winner: Optional[SolverType]
    time_difference_ms: int

@dataclass
class RaceStatus:
    solver_type: SolverType
    states_explored: int
    elapsed_ms: int
    is_complete: bool