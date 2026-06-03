"""Performance recording and statistical analysis for the Sudoku Solver Evaluator.

Implements the PerformanceEvaluatorProtocol to record solve results,
compute per-puzzle rankings, and aggregate statistics across difficulty levels.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType
from sudoku_solver_evaluator.models.metrics import (
    AggregateStats,
    AlgorithmStats,
    ComparisonTable,
    SolveResult,
)
from sudoku_solver_evaluator.models.protocols import PerformanceEvaluatorProtocol


class PerformanceEvaluator(PerformanceEvaluatorProtocol):
    """Records solve results and computes performance statistics.

    Stores results keyed by puzzle_id and difficulty level, enabling
    per-puzzle comparisons and cross-puzzle aggregate statistics.

    Attributes:
        _results: Mapping of puzzle_id to dict of solver_type -> SolveResult.
        _difficulty_map: Mapping of puzzle_id to its DifficultyLevel.
        _difficulty_results: Mapping of difficulty to list of (puzzle_id, solver_type, result).
    """

    def __init__(self) -> None:
        """Initialize the performance evaluator with empty data stores."""
        # puzzle_id -> {solver_type -> SolveResult}
        self._results: dict[str, dict[SolverType, SolveResult]] = defaultdict(dict)
        # puzzle_id -> DifficultyLevel
        self._difficulty_map: dict[str, DifficultyLevel] = {}
        # difficulty -> list of (puzzle_id, solver_type, SolveResult)
        self._difficulty_results: dict[DifficultyLevel, list[tuple[str, SolverType, SolveResult]]] = defaultdict(list)

    def record(self, result: SolveResult, puzzle_id: str, difficulty: DifficultyLevel) -> None:
        """Record a solve result for later analysis.

        Stores the result keyed by puzzle_id and solver_type. Timeout and
        failed results are recorded with their partial metrics (time, states,
        backtracks) so they can still contribute to aggregate statistics.

        Args:
            result: The SolveResult from a solver run.
            puzzle_id: Unique identifier for the puzzle that was solved.
            difficulty: The difficulty level of the puzzle.
        """
        self._results[puzzle_id][result.solver_type] = result
        self._difficulty_map[puzzle_id] = difficulty
        self._difficulty_results[difficulty].append((puzzle_id, result.solver_type, result))

    def get_comparison(self, puzzle_id: str) -> ComparisonTable:
        """Get comparison data for all algorithms on a given puzzle.

        Computes rankings based on states_explored in ascending order.
        Algorithms with fewer states explored are ranked higher (more efficient).

        Args:
            puzzle_id: The unique identifier of the puzzle to compare.

        Returns:
            ComparisonTable with results and rankings for the puzzle.

        Raises:
            KeyError: If no results have been recorded for the given puzzle_id.
        """
        if puzzle_id not in self._results:
            raise KeyError(f"No results recorded for puzzle_id: {puzzle_id}")

        results = self._results[puzzle_id]
        difficulty = self._difficulty_map[puzzle_id]

        # Compute rankings by states_explored (ascending - fewer is better)
        rankings = self._compute_rankings(results)

        return ComparisonTable(
            puzzle_id=puzzle_id,
            difficulty=difficulty,
            results=dict(results),
            rankings=rankings,
        )

    def get_aggregate(self, difficulty: DifficultyLevel) -> AggregateStats:
        """Get aggregate statistics for a difficulty level.

        Computes mean, min, and max for time_ms, states_explored, backtracks,
        and solve_rate across all puzzles of the specified difficulty level.
        Requires a minimum of 5 puzzles for meaningful statistics.

        Args:
            difficulty: The difficulty level to aggregate over.

        Returns:
            AggregateStats with per-algorithm statistics. If fewer than 5
            puzzles have been recorded, returns stats with puzzle_count
            reflecting actual count (stats may be less meaningful).
        """
        # Collect results grouped by solver_type for this difficulty
        solver_results: dict[SolverType, list[SolveResult]] = defaultdict(list)

        # Get unique puzzle_ids for this difficulty
        puzzle_ids = {
            pid for pid, diff in self._difficulty_map.items() if diff == difficulty
        }
        puzzle_count = len(puzzle_ids)

        # Group results by solver
        for puzzle_id in puzzle_ids:
            for solver_type, result in self._results[puzzle_id].items():
                solver_results[solver_type].append(result)

        # Compute stats per solver
        stats: dict[SolverType, AlgorithmStats] = {}
        for solver_type, results_list in solver_results.items():
            stats[solver_type] = self._compute_algorithm_stats(results_list)

        return AggregateStats(
            difficulty=difficulty,
            puzzle_count=puzzle_count,
            stats=stats,
        )

    def export_csv(self, filepath: str) -> None:
        """Export all recorded results to CSV.

        Delegates to the CSV exporter module for the actual file writing.

        Args:
            filepath: The file path where the CSV will be written.

        Raises:
            ExportError: If the file cannot be written.
        """
        from sudoku_solver_evaluator.evaluator.exporter import export_results_csv

        export_results_csv(self._results, self._difficulty_map, filepath)

    def _compute_rankings(
        self, results: dict[SolverType, SolveResult]
    ) -> dict[str, list[SolverType]]:
        """Compute rankings for a set of results on a single puzzle.

        Rankings are computed for the following metrics:
        - states_explored: ascending (fewer is better)
        - time_ms: ascending (faster is better)
        - backtracks: ascending (fewer is better)

        Args:
            results: Mapping of solver_type to SolveResult for one puzzle.

        Returns:
            Dictionary mapping metric name to list of SolverTypes ordered
            from best (index 0) to worst.
        """
        rankings: dict[str, list[SolverType]] = {}

        # Rank by states_explored (ascending - fewer is more efficient)
        rankings["states_explored"] = sorted(
            results.keys(), key=lambda st: results[st].states_explored
        )

        # Rank by time_ms (ascending - faster is better)
        rankings["time_ms"] = sorted(
            results.keys(), key=lambda st: results[st].time_ms
        )

        # Rank by backtracks (ascending - fewer is better)
        rankings["backtracks"] = sorted(
            results.keys(), key=lambda st: results[st].backtracks
        )

        return rankings

    def _compute_algorithm_stats(self, results: list[SolveResult]) -> AlgorithmStats:
        """Compute aggregate statistics for a single algorithm.

        Handles timeout/failed results by including their partial metrics
        in the calculations. Solve rate is computed as the fraction of
        results with SOLVED status.

        Args:
            results: List of SolveResult objects for one algorithm.

        Returns:
            AlgorithmStats with mean/min/max for time, states, backtracks,
            and the solve rate.
        """
        if not results:
            return AlgorithmStats(
                mean_time_ms=0.0,
                min_time_ms=0,
                max_time_ms=0,
                mean_states=0.0,
                min_states=0,
                max_states=0,
                mean_backtracks=0.0,
                min_backtracks=0,
                max_backtracks=0,
                solve_rate=0.0,
            )

        times = [r.time_ms for r in results]
        states = [r.states_explored for r in results]
        backtracks = [r.backtracks for r in results]
        solved_count = sum(1 for r in results if r.status == SolveStatus.SOLVED)

        n = len(results)

        return AlgorithmStats(
            mean_time_ms=sum(times) / n,
            min_time_ms=min(times),
            max_time_ms=max(times),
            mean_states=sum(states) / n,
            min_states=min(states),
            max_states=max(states),
            mean_backtracks=sum(backtracks) / n,
            min_backtracks=min(backtracks),
            max_backtracks=max(backtracks),
            solve_rate=solved_count / n,
        )

    def get_all_results(self) -> dict[str, dict[SolverType, SolveResult]]:
        """Get all recorded results.

        Returns:
            Dictionary mapping puzzle_id to solver results dictionary.
        """
        return dict(self._results)

    def get_difficulty_map(self) -> dict[str, DifficultyLevel]:
        """Get the mapping of puzzle_ids to difficulty levels.

        Returns:
            Dictionary mapping puzzle_id to DifficultyLevel.
        """
        return dict(self._difficulty_map)
