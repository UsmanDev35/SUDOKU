from enum import Enum

class DifficultyLevel(Enum):
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'
    EXPERT = 'expert'

class SolverType(Enum):
    BACKTRACKING = 'backtracking'
    INFORMED = 'informed'
    LOCAL_SEARCH = 'local_search'
    FORWARD_CHECKING = 'forward_checking'

class SolveStatus(Enum):
    SOLVED = 'solved'
    UNSOLVABLE = 'unsolvable'
    TIMEOUT = 'timeout'
    FAILED = 'failed'

class StepType(Enum):
    ASSIGN = 'assign'
    BACKTRACK = 'backtrack'
    SWAP = 'swap'
    PROPAGATE = 'propagate'