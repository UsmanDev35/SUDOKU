"""Enumerations for the Sudoku Solver and Evaluator system.

Defines difficulty levels, solver types, solve statuses, and step types
used throughout the application.
"""

from enum import Enum


class DifficultyLevel(Enum):
    """Difficulty levels for puzzle generation.

    Each level determines the number of pre-filled cells in a generated puzzle:
        - EASY: 36-45 pre-filled cells
        - MEDIUM: 27-35 pre-filled cells
        - HARD: 22-26 pre-filled cells
        - EXPERT: 17-21 pre-filled cells
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class SolverType(Enum):
    """Types of solver algorithms available in the system.

    Each solver implements a different AI search strategy:
        - BACKTRACKING: Uninformed depth-first search
        - INFORMED: AC-3 with MRV and Degree Heuristic
        - LOCAL_SEARCH: Simulated Annealing
        - FORWARD_CHECKING: Constraint Propagation with Forward Checking
    """

    BACKTRACKING = "backtracking"
    INFORMED = "informed"
    LOCAL_SEARCH = "local_search"
    FORWARD_CHECKING = "forward_checking"


class SolveStatus(Enum):
    """Status outcomes for a solve operation.

    Attributes:
        SOLVED: Puzzle was solved successfully.
        UNSOLVABLE: Puzzle has no valid solution (constraint violations detected).
        TIMEOUT: Solver exceeded the configured time limit.
        FAILED: Solver exhausted its strategy without finding a solution (e.g., SA max restarts).
    """

    SOLVED = "solved"
    UNSOLVABLE = "unsolvable"
    TIMEOUT = "timeout"
    FAILED = "failed"


class StepType(Enum):
    """Types of step events emitted during the solving process.

    Used for step-by-step visualization:
        - ASSIGN: A value was assigned to a cell.
        - BACKTRACK: An assignment was undone.
        - SWAP: Two cells were swapped (Simulated Annealing).
        - PROPAGATE: A domain was reduced via constraint propagation.
    """

    ASSIGN = "assign"
    BACKTRACK = "backtrack"
    SWAP = "swap"
    PROPAGATE = "propagate"
