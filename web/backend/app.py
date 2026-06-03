"""FastAPI backend for the Sudoku Solver Evaluator web UI.

Provides REST API endpoints for puzzle generation, solving, adversarial racing,
and performance statistics.
"""

import sys
import uuid
from pathlib import Path

# Add the project root to sys.path so we can import the solver package
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolverType, SolveStatus
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.adversarial.race import RaceController

app = FastAPI(title="Sudoku Solver Evaluator API", version="1.0.0")

# CORS middleware for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
generator = PuzzleGenerator()
solver_manager = SolverManager()
evaluator = PerformanceEvaluator()
race_controller = RaceController(solver_manager)

# Store generated puzzles for reference
puzzle_store: dict[str, dict] = {}

# --- Request/Response Models ---

DIFFICULTY_MAP = {
    "easy": DifficultyLevel.EASY,
    "medium": DifficultyLevel.MEDIUM,
    "hard": DifficultyLevel.HARD,
    "expert": DifficultyLevel.EXPERT,
}

SOLVER_MAP = {
    "backtracking": SolverType.BACKTRACKING,
    "informed": SolverType.INFORMED,
    "local_search": SolverType.LOCAL_SEARCH,
    "forward_checking": SolverType.FORWARD_CHECKING,
}


class GenerateRequest(BaseModel):
    difficulty: str = Field(..., pattern="^(easy|medium|hard|expert)$")


class GenerateResponse(BaseModel):
    puzzle_id: str
    puzzle: list[list[int]]
    difficulty: str
    filled_cells: int


class SolveRequest(BaseModel):
    puzzle: list[list[int]]
    solver: str = Field(..., pattern="^(backtracking|informed|local_search|forward_checking|all)$")


class SolverResult(BaseModel):
    solver: str
    status: str
    time_ms: int
    states_explored: int
    backtracks: int
    solution: Optional[list[list[int]]] = None


class SolveResponse(BaseModel):
    results: list[SolverResult]


class RaceRequest(BaseModel):
    puzzle: list[list[int]]
    solver_a: str = Field(..., pattern="^(backtracking|informed|local_search|forward_checking)$")
    solver_b: str = Field(..., pattern="^(backtracking|informed|local_search|forward_checking)$")


class RaceResponse(BaseModel):
    winner: Optional[str]
    time_difference_ms: int
    solver_a: SolverResult
    solver_b: SolverResult


class AlgorithmStatsResponse(BaseModel):
    solver: str
    mean_time_ms: float
    min_time_ms: int
    max_time_ms: int
    mean_states: float
    min_states: int
    max_states: int
    mean_backtracks: float
    solve_rate: float


class DifficultyStatsResponse(BaseModel):
    difficulty: str
    puzzle_count: int
    algorithms: list[AlgorithmStatsResponse]


class StatsResponse(BaseModel):
    difficulties: list[DifficultyStatsResponse]


# --- Endpoints ---

@app.post("/api/generate", response_model=GenerateResponse)
def generate_puzzle(request: GenerateRequest):
    """Generate a new Sudoku puzzle at the specified difficulty."""
    difficulty = DIFFICULTY_MAP.get(request.difficulty)
    if not difficulty:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty: {request.difficulty}")

    try:
        grid = generator.generate(difficulty, timeout=30.0)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Puzzle generation timed out")

    puzzle_2d = grid.to_2d_list()
    puzzle_id = str(uuid.uuid4())

    # Store for later use
    puzzle_store[puzzle_id] = {
        "puzzle": puzzle_2d,
        "difficulty": request.difficulty,
    }

    return GenerateResponse(
        puzzle_id=puzzle_id,
        puzzle=puzzle_2d,
        difficulty=request.difficulty,
        filled_cells=grid.count_filled(),
    )


@app.post("/api/solve", response_model=SolveResponse)
def solve_puzzle(request: SolveRequest):
    """Solve a puzzle using the specified solver(s)."""
    # Validate puzzle dimensions
    if len(request.puzzle) != 9 or any(len(row) != 9 for row in request.puzzle):
        raise HTTPException(status_code=400, detail="Puzzle must be a 9x9 grid")

    grid = Grid.from_2d_list(request.puzzle)
    results: list[SolverResult] = []

    if request.solver == "all":
        # Run all solvers
        all_results = solver_manager.solve_all(grid, timeout=60.0)
        for solver_type, result in all_results.items():
            solution = result.solved_grid.to_2d_list() if result.solved_grid else None
            results.append(SolverResult(
                solver=solver_type.value,
                status=result.status.value,
                time_ms=result.time_ms,
                states_explored=result.states_explored,
                backtracks=result.backtracks,
                solution=solution,
            ))
    else:
        solver_type = SOLVER_MAP.get(request.solver)
        if not solver_type:
            raise HTTPException(status_code=400, detail=f"Invalid solver: {request.solver}")

        result = solver_manager.solve(grid, solver_type, timeout=60.0)
        solution = result.solved_grid.to_2d_list() if result.solved_grid else None
        results.append(SolverResult(
            solver=solver_type.value,
            status=result.status.value,
            time_ms=result.time_ms,
            states_explored=result.states_explored,
            backtracks=result.backtracks,
            solution=solution,
        ))

    # Record results for statistics
    puzzle_id = str(uuid.uuid4())
    for r in results:
        solver_t = SOLVER_MAP[r.solver]
        from sudoku_solver_evaluator.models.metrics import SolveResult as SR
        sr = SR(
            solver_type=solver_t,
            status=SolveStatus(r.status),
            time_ms=r.time_ms,
            states_explored=r.states_explored,
            backtracks=r.backtracks,
        )
        evaluator.record(sr, puzzle_id, DifficultyLevel.MEDIUM)

    return SolveResponse(results=results)


@app.post("/api/race", response_model=RaceResponse)
def run_race(request: RaceRequest):
    """Run an adversarial race between two solvers."""
    if request.solver_a == request.solver_b:
        raise HTTPException(status_code=400, detail="Must select two different solvers")

    solver_a = SOLVER_MAP.get(request.solver_a)
    solver_b = SOLVER_MAP.get(request.solver_b)

    if not solver_a or not solver_b:
        raise HTTPException(status_code=400, detail="Invalid solver selection")

    # Validate puzzle dimensions
    if len(request.puzzle) != 9 or any(len(row) != 9 for row in request.puzzle):
        raise HTTPException(status_code=400, detail="Puzzle must be a 9x9 grid")

    grid = Grid.from_2d_list(request.puzzle)

    try:
        race_result = race_controller.start_race(grid, solver_a, solver_b, timeout=60.0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build response
    sol_a = race_result.solver_a_result
    sol_b = race_result.solver_b_result

    return RaceResponse(
        winner=race_result.winner.value if race_result.winner else None,
        time_difference_ms=race_result.time_difference_ms,
        solver_a=SolverResult(
            solver=sol_a.solver_type.value,
            status=sol_a.status.value,
            time_ms=sol_a.time_ms,
            states_explored=sol_a.states_explored,
            backtracks=sol_a.backtracks,
            solution=sol_a.solved_grid.to_2d_list() if sol_a.solved_grid else None,
        ),
        solver_b=SolverResult(
            solver=sol_b.solver_type.value,
            status=sol_b.status.value,
            time_ms=sol_b.time_ms,
            states_explored=sol_b.states_explored,
            backtracks=sol_b.backtracks,
            solution=sol_b.solved_grid.to_2d_list() if sol_b.solved_grid else None,
        ),
    )


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """Get aggregate statistics for all difficulty levels."""
    difficulties_response: list[DifficultyStatsResponse] = []

    for diff_name, diff_enum in DIFFICULTY_MAP.items():
        agg = evaluator.get_aggregate(diff_enum)
        algorithms: list[AlgorithmStatsResponse] = []

        for solver_type, algo_stats in agg.stats.items():
            algorithms.append(AlgorithmStatsResponse(
                solver=solver_type.value,
                mean_time_ms=round(algo_stats.mean_time_ms, 2),
                min_time_ms=algo_stats.min_time_ms,
                max_time_ms=algo_stats.max_time_ms,
                mean_states=round(algo_stats.mean_states, 2),
                min_states=algo_stats.min_states,
                max_states=algo_stats.max_states,
                mean_backtracks=round(algo_stats.mean_backtracks, 2),
                solve_rate=round(algo_stats.solve_rate, 4),
            ))

        difficulties_response.append(DifficultyStatsResponse(
            difficulty=diff_name,
            puzzle_count=agg.puzzle_count,
            algorithms=algorithms,
        ))

    return StatsResponse(difficulties=difficulties_response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
