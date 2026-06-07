from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType
from sudoku_solver_evaluator.models.metrics import AggregateStats, AlgorithmStats, ComparisonTable, SolveResult
from sudoku_solver_evaluator.models.protocols import PerformanceEvaluatorProtocol

class PerformanceEvaluator(PerformanceEvaluatorProtocol):

    def __init__(self) -> None:
        self._results: dict[str, dict[SolverType, SolveResult]] = defaultdict(dict)
        self._difficulty_map: dict[str, DifficultyLevel] = {}
        self._difficulty_results: dict[DifficultyLevel, list[tuple[str, SolverType, SolveResult]]] = defaultdict(list)

    def record(self, result: SolveResult, puzzle_id: str, difficulty: DifficultyLevel) -> None:
        self._results[puzzle_id][result.solver_type] = result
        self._difficulty_map[puzzle_id] = difficulty
        self._difficulty_results[difficulty].append((puzzle_id, result.solver_type, result))

    def get_comparison(self, puzzle_id: str) -> ComparisonTable:
        if puzzle_id not in self._results:
            raise KeyError(f'No results recorded for puzzle_id: {puzzle_id}')
        results = self._results[puzzle_id]
        difficulty = self._difficulty_map[puzzle_id]
        rankings = self._compute_rankings(results)
        return ComparisonTable(puzzle_id=puzzle_id, difficulty=difficulty, results=dict(results), rankings=rankings)

    def get_aggregate(self, difficulty: DifficultyLevel) -> AggregateStats:
        solver_results: dict[SolverType, list[SolveResult]] = defaultdict(list)
        puzzle_ids = {pid for pid, diff in self._difficulty_map.items() if diff == difficulty}
        puzzle_count = len(puzzle_ids)
        for puzzle_id in puzzle_ids:
            for solver_type, result in self._results[puzzle_id].items():
                solver_results[solver_type].append(result)
        stats: dict[SolverType, AlgorithmStats] = {}
        for solver_type, results_list in solver_results.items():
            stats[solver_type] = self._compute_algorithm_stats(results_list)
        return AggregateStats(difficulty=difficulty, puzzle_count=puzzle_count, stats=stats)

    def export_csv(self, filepath: str) -> None:
        from sudoku_solver_evaluator.evaluator.exporter import export_results_csv
        export_results_csv(self._results, self._difficulty_map, filepath)

    def _compute_rankings(self, results: dict[SolverType, SolveResult]) -> dict[str, list[SolverType]]:
        rankings: dict[str, list[SolverType]] = {}
        rankings['states_explored'] = sorted(results.keys(), key=lambda st: results[st].states_explored)
        rankings['time_ms'] = sorted(results.keys(), key=lambda st: results[st].time_ms)
        rankings['backtracks'] = sorted(results.keys(), key=lambda st: results[st].backtracks)
        return rankings

    def _compute_algorithm_stats(self, results: list[SolveResult]) -> AlgorithmStats:
        if not results:
            return AlgorithmStats(mean_time_ms=0.0, min_time_ms=0, max_time_ms=0, mean_states=0.0, min_states=0, max_states=0, mean_backtracks=0.0, min_backtracks=0, max_backtracks=0, solve_rate=0.0)
        times = [r.time_ms for r in results]
        states = [r.states_explored for r in results]
        backtracks = [r.backtracks for r in results]
        solved_count = sum((1 for r in results if r.status == SolveStatus.SOLVED))
        n = len(results)
        return AlgorithmStats(mean_time_ms=sum(times) / n, min_time_ms=min(times), max_time_ms=max(times), mean_states=sum(states) / n, min_states=min(states), max_states=max(states), mean_backtracks=sum(backtracks) / n, min_backtracks=min(backtracks), max_backtracks=max(backtracks), solve_rate=solved_count / n)

    def get_all_results(self) -> dict[str, dict[SolverType, SolveResult]]:
        return dict(self._results)

    def get_difficulty_map(self) -> dict[str, DifficultyLevel]:
        return dict(self._difficulty_map)