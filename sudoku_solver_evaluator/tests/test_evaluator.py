"""Unit tests for the Performance Evaluator module.

Tests recording of solve results, per-puzzle comparison/rankings,
aggregate statistics computation, and handling of timeout results.
"""

import pytest

from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType
from sudoku_solver_evaluator.models.metrics import SolveResult


def _make_result(
    solver_type: SolverType,
    status: SolveStatus = SolveStatus.SOLVED,
    time_ms: int = 100,
    states_explored: int = 50,
    backtracks: int = 10,
) -> SolveResult:
    """Helper to create a SolveResult with specified metrics."""
    return SolveResult(
        solver_type=solver_type,
        status=status,
        time_ms=time_ms,
        states_explored=states_explored,
        backtracks=backtracks,
    )


class TestPerformanceEvaluatorRecord:
    """Tests for recording solve results."""

    def test_record_single_result(self) -> None:
        evaluator = PerformanceEvaluator()
        result = _make_result(SolverType.BACKTRACKING)
        evaluator.record(result, "puzzle_1", DifficultyLevel.EASY)

        all_results = evaluator.get_all_results()
        assert "puzzle_1" in all_results
        assert SolverType.BACKTRACKING in all_results["puzzle_1"]
        assert all_results["puzzle_1"][SolverType.BACKTRACKING] is result

    def test_record_multiple_solvers_same_puzzle(self) -> None:
        evaluator = PerformanceEvaluator()
        r1 = _make_result(SolverType.BACKTRACKING, states_explored=100)
        r2 = _make_result(SolverType.INFORMED, states_explored=30)
        evaluator.record(r1, "puzzle_1", DifficultyLevel.MEDIUM)
        evaluator.record(r2, "puzzle_1", DifficultyLevel.MEDIUM)

        all_results = evaluator.get_all_results()
        assert len(all_results["puzzle_1"]) == 2

    def test_record_timeout_result(self) -> None:
        evaluator = PerformanceEvaluator()
        result = _make_result(
            SolverType.LOCAL_SEARCH,
            status=SolveStatus.TIMEOUT,
            time_ms=60000,
            states_explored=5000,
            backtracks=0,
        )
        evaluator.record(result, "puzzle_1", DifficultyLevel.HARD)

        all_results = evaluator.get_all_results()
        recorded = all_results["puzzle_1"][SolverType.LOCAL_SEARCH]
        assert recorded.status == SolveStatus.TIMEOUT
        assert recorded.time_ms == 60000
        assert recorded.states_explored == 5000

    def test_record_overwrite_same_solver(self) -> None:
        evaluator = PerformanceEvaluator()
        r1 = _make_result(SolverType.BACKTRACKING, states_explored=100)
        r2 = _make_result(SolverType.BACKTRACKING, states_explored=50)
        evaluator.record(r1, "puzzle_1", DifficultyLevel.EASY)
        evaluator.record(r2, "puzzle_1", DifficultyLevel.EASY)

        all_results = evaluator.get_all_results()
        assert all_results["puzzle_1"][SolverType.BACKTRACKING].states_explored == 50


class TestPerformanceEvaluatorComparison:
    """Tests for get_comparison method."""

    def test_comparison_single_solver(self) -> None:
        evaluator = PerformanceEvaluator()
        result = _make_result(SolverType.BACKTRACKING, states_explored=100)
        evaluator.record(result, "puzzle_1", DifficultyLevel.EASY)

        comparison = evaluator.get_comparison("puzzle_1")
        assert comparison.puzzle_id == "puzzle_1"
        assert comparison.difficulty == DifficultyLevel.EASY
        assert SolverType.BACKTRACKING in comparison.results
        assert comparison.rankings["states_explored"] == [SolverType.BACKTRACKING]

    def test_comparison_rankings_by_states_explored(self) -> None:
        evaluator = PerformanceEvaluator()
        evaluator.record(
            _make_result(SolverType.BACKTRACKING, states_explored=200),
            "puzzle_1",
            DifficultyLevel.MEDIUM,
        )
        evaluator.record(
            _make_result(SolverType.INFORMED, states_explored=50),
            "puzzle_1",
            DifficultyLevel.MEDIUM,
        )
        evaluator.record(
            _make_result(SolverType.FORWARD_CHECKING, states_explored=80),
            "puzzle_1",
            DifficultyLevel.MEDIUM,
        )
        evaluator.record(
            _make_result(SolverType.LOCAL_SEARCH, states_explored=1000),
            "puzzle_1",
            DifficultyLevel.MEDIUM,
        )

        comparison = evaluator.get_comparison("puzzle_1")
        ranking = comparison.rankings["states_explored"]
        # Should be sorted ascending: INFORMED(50), FC(80), BT(200), LS(1000)
        assert ranking[0] == SolverType.INFORMED
        assert ranking[1] == SolverType.FORWARD_CHECKING
        assert ranking[2] == SolverType.BACKTRACKING
        assert ranking[3] == SolverType.LOCAL_SEARCH

    def test_comparison_rankings_by_time(self) -> None:
        evaluator = PerformanceEvaluator()
        evaluator.record(
            _make_result(SolverType.BACKTRACKING, time_ms=500),
            "puzzle_1",
            DifficultyLevel.EASY,
        )
        evaluator.record(
            _make_result(SolverType.INFORMED, time_ms=100),
            "puzzle_1",
            DifficultyLevel.EASY,
        )

        comparison = evaluator.get_comparison("puzzle_1")
        assert comparison.rankings["time_ms"][0] == SolverType.INFORMED
        assert comparison.rankings["time_ms"][1] == SolverType.BACKTRACKING

    def test_comparison_unknown_puzzle_raises(self) -> None:
        evaluator = PerformanceEvaluator()
        with pytest.raises(KeyError):
            evaluator.get_comparison("nonexistent")


class TestPerformanceEvaluatorAggregate:
    """Tests for get_aggregate method."""

    def test_aggregate_with_5_puzzles(self) -> None:
        evaluator = PerformanceEvaluator()
        # Record 5 puzzles, each with backtracking solver
        for i in range(5):
            result = _make_result(
                SolverType.BACKTRACKING,
                time_ms=(i + 1) * 100,  # 100, 200, 300, 400, 500
                states_explored=(i + 1) * 10,  # 10, 20, 30, 40, 50
                backtracks=(i + 1) * 2,  # 2, 4, 6, 8, 10
            )
            evaluator.record(result, f"puzzle_{i}", DifficultyLevel.EASY)

        aggregate = evaluator.get_aggregate(DifficultyLevel.EASY)
        assert aggregate.difficulty == DifficultyLevel.EASY
        assert aggregate.puzzle_count == 5

        bt_stats = aggregate.stats[SolverType.BACKTRACKING]
        assert bt_stats.mean_time_ms == 300.0
        assert bt_stats.min_time_ms == 100
        assert bt_stats.max_time_ms == 500
        assert bt_stats.mean_states == 30.0
        assert bt_stats.min_states == 10
        assert bt_stats.max_states == 50
        assert bt_stats.mean_backtracks == 6.0
        assert bt_stats.min_backtracks == 2
        assert bt_stats.max_backtracks == 10
        assert bt_stats.solve_rate == 1.0

    def test_aggregate_with_timeouts_affects_solve_rate(self) -> None:
        evaluator = PerformanceEvaluator()
        # 3 solved, 2 timed out
        for i in range(3):
            evaluator.record(
                _make_result(SolverType.BACKTRACKING, status=SolveStatus.SOLVED),
                f"puzzle_{i}",
                DifficultyLevel.HARD,
            )
        for i in range(3, 5):
            evaluator.record(
                _make_result(SolverType.BACKTRACKING, status=SolveStatus.TIMEOUT),
                f"puzzle_{i}",
                DifficultyLevel.HARD,
            )

        aggregate = evaluator.get_aggregate(DifficultyLevel.HARD)
        bt_stats = aggregate.stats[SolverType.BACKTRACKING]
        assert bt_stats.solve_rate == pytest.approx(0.6)

    def test_aggregate_empty_difficulty(self) -> None:
        evaluator = PerformanceEvaluator()
        aggregate = evaluator.get_aggregate(DifficultyLevel.EXPERT)
        assert aggregate.puzzle_count == 0
        assert aggregate.stats == {}

    def test_aggregate_multiple_solvers(self) -> None:
        evaluator = PerformanceEvaluator()
        for i in range(5):
            evaluator.record(
                _make_result(SolverType.BACKTRACKING, states_explored=100),
                f"puzzle_{i}",
                DifficultyLevel.MEDIUM,
            )
            evaluator.record(
                _make_result(SolverType.INFORMED, states_explored=30),
                f"puzzle_{i}",
                DifficultyLevel.MEDIUM,
            )

        aggregate = evaluator.get_aggregate(DifficultyLevel.MEDIUM)
        assert aggregate.puzzle_count == 5
        assert SolverType.BACKTRACKING in aggregate.stats
        assert SolverType.INFORMED in aggregate.stats
        assert aggregate.stats[SolverType.BACKTRACKING].mean_states == 100.0
        assert aggregate.stats[SolverType.INFORMED].mean_states == 30.0

    def test_aggregate_partial_metrics_from_timeout(self) -> None:
        """Timeout results should have their partial metrics included."""
        evaluator = PerformanceEvaluator()
        for i in range(5):
            evaluator.record(
                _make_result(
                    SolverType.LOCAL_SEARCH,
                    status=SolveStatus.TIMEOUT,
                    time_ms=60000,
                    states_explored=5000 + i * 100,
                    backtracks=0,
                ),
                f"puzzle_{i}",
                DifficultyLevel.EXPERT,
            )

        aggregate = evaluator.get_aggregate(DifficultyLevel.EXPERT)
        ls_stats = aggregate.stats[SolverType.LOCAL_SEARCH]
        # Even timeout results contribute their partial metrics
        assert ls_stats.mean_time_ms == 60000.0
        assert ls_stats.min_states == 5000
        assert ls_stats.max_states == 5400
        assert ls_stats.solve_rate == 0.0


class TestPerformanceEvaluatorDifficultyMap:
    """Tests for difficulty mapping."""

    def test_difficulty_map_stored_correctly(self) -> None:
        evaluator = PerformanceEvaluator()
        evaluator.record(
            _make_result(SolverType.BACKTRACKING),
            "puzzle_1",
            DifficultyLevel.EASY,
        )
        evaluator.record(
            _make_result(SolverType.BACKTRACKING),
            "puzzle_2",
            DifficultyLevel.HARD,
        )

        diff_map = evaluator.get_difficulty_map()
        assert diff_map["puzzle_1"] == DifficultyLevel.EASY
        assert diff_map["puzzle_2"] == DifficultyLevel.HARD
