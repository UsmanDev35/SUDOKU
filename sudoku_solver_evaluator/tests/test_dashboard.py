"""Unit tests for the comparative analysis dashboard.

Tests rendering of comparison tables, aggregate statistics,
performance charts, and grouped display.
"""

from io import StringIO

from rich.console import Console

from sudoku_solver_evaluator.models.enums import (
    DifficultyLevel,
    SolveStatus,
    SolverType,
)
from sudoku_solver_evaluator.models.metrics import (
    AggregateStats,
    AlgorithmStats,
    ComparisonTable,
    SolveResult,
)
from sudoku_solver_evaluator.ui.dashboard import (
    render_aggregate_table,
    render_comparison_table,
    render_full_dashboard,
    render_grouped_by_difficulty,
    render_performance_chart,
)


def _make_console() -> tuple[Console, StringIO]:
    """Create a Console that captures output to a StringIO buffer."""
    buffer = StringIO()
    console = Console(file=buffer, width=120, force_terminal=True)
    return console, buffer


def _sample_results() -> dict[SolverType, SolveResult]:
    """Create sample solve results for testing."""
    return {
        SolverType.BACKTRACKING: SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            time_ms=1200,
            states_explored=5000,
            backtracks=800,
        ),
        SolverType.INFORMED: SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.SOLVED,
            time_ms=150,
            states_explored=200,
            backtracks=20,
        ),
        SolverType.LOCAL_SEARCH: SolveResult(
            solver_type=SolverType.LOCAL_SEARCH,
            status=SolveStatus.SOLVED,
            time_ms=800,
            states_explored=3000,
            backtracks=0,
        ),
        SolverType.FORWARD_CHECKING: SolveResult(
            solver_type=SolverType.FORWARD_CHECKING,
            status=SolveStatus.SOLVED,
            time_ms=100,
            states_explored=150,
            backtracks=10,
        ),
    }


def _sample_comparison() -> ComparisonTable:
    """Create a sample ComparisonTable for testing."""
    results = _sample_results()
    rankings = {
        "states_explored": [
            SolverType.FORWARD_CHECKING,
            SolverType.INFORMED,
            SolverType.LOCAL_SEARCH,
            SolverType.BACKTRACKING,
        ],
        "time_ms": [
            SolverType.FORWARD_CHECKING,
            SolverType.INFORMED,
            SolverType.LOCAL_SEARCH,
            SolverType.BACKTRACKING,
        ],
        "backtracks": [
            SolverType.LOCAL_SEARCH,
            SolverType.FORWARD_CHECKING,
            SolverType.INFORMED,
            SolverType.BACKTRACKING,
        ],
    }
    return ComparisonTable(
        puzzle_id="test-puzzle-001",
        difficulty=DifficultyLevel.MEDIUM,
        results=results,
        rankings=rankings,
    )


def _sample_aggregate() -> AggregateStats:
    """Create sample AggregateStats for testing."""
    return AggregateStats(
        difficulty=DifficultyLevel.MEDIUM,
        puzzle_count=10,
        stats={
            SolverType.BACKTRACKING: AlgorithmStats(
                mean_time_ms=1100.5,
                min_time_ms=800,
                max_time_ms=1500,
                mean_states=4500.0,
                min_states=3000,
                max_states=6000,
                mean_backtracks=700.0,
                min_backtracks=500,
                max_backtracks=900,
                solve_rate=1.0,
            ),
            SolverType.INFORMED: AlgorithmStats(
                mean_time_ms=120.3,
                min_time_ms=80,
                max_time_ms=200,
                mean_states=180.0,
                min_states=100,
                max_states=300,
                mean_backtracks=15.0,
                min_backtracks=5,
                max_backtracks=30,
                solve_rate=1.0,
            ),
            SolverType.LOCAL_SEARCH: AlgorithmStats(
                mean_time_ms=900.0,
                min_time_ms=500,
                max_time_ms=1400,
                mean_states=3200.0,
                min_states=2000,
                max_states=5000,
                mean_backtracks=0.0,
                min_backtracks=0,
                max_backtracks=0,
                solve_rate=0.8,
            ),
            SolverType.FORWARD_CHECKING: AlgorithmStats(
                mean_time_ms=90.0,
                min_time_ms=60,
                max_time_ms=150,
                mean_states=130.0,
                min_states=80,
                max_states=200,
                mean_backtracks=8.0,
                min_backtracks=2,
                max_backtracks=20,
                solve_rate=1.0,
            ),
        },
    )


class TestRenderComparisonTable:
    """Tests for render_comparison_table function."""

    def test_renders_without_error(self) -> None:
        """Comparison table renders without raising exceptions."""
        console, buffer = _make_console()
        comparison = _sample_comparison()
        render_comparison_table(comparison, console=console)
        output = buffer.getvalue()
        assert len(output) > 0

    def test_displays_puzzle_id(self) -> None:
        """Output contains the puzzle ID."""
        console, buffer = _make_console()
        comparison = _sample_comparison()
        render_comparison_table(comparison, console=console)
        output = buffer.getvalue()
        assert "test-puzzle-001" in output

    def test_displays_difficulty(self) -> None:
        """Output contains the difficulty level."""
        console, buffer = _make_console()
        comparison = _sample_comparison()
        render_comparison_table(comparison, console=console)
        output = buffer.getvalue()
        assert "Medium" in output

    def test_displays_all_algorithms(self) -> None:
        """Output shows all four algorithm names."""
        console, buffer = _make_console()
        comparison = _sample_comparison()
        render_comparison_table(comparison, console=console)
        output = buffer.getvalue()
        assert "Backtracking" in output
        assert "Informed" in output
        assert "Simulated Annealing" in output
        assert "Forward Checking" in output

    def test_displays_metric_values(self) -> None:
        """Output shows actual metric values."""
        console, buffer = _make_console()
        comparison = _sample_comparison()
        render_comparison_table(comparison, console=console)
        output = buffer.getvalue()
        # Check some metric values are present
        assert "5,000" in output  # bactracking states
        assert "150" in output  # forward checking states or informed time

    def test_empty_results_shows_message(self) -> None:
        """Empty results dict shows a warning message."""
        console, buffer = _make_console()
        comparison = ComparisonTable(
            puzzle_id="empty",
            difficulty=DifficultyLevel.EASY,
            results={},
            rankings={},
        )
        render_comparison_table(comparison, console=console)
        output = buffer.getvalue()
        assert "No results" in output


class TestRenderAggregateTable:
    """Tests for render_aggregate_table function."""

    def test_renders_without_error(self) -> None:
        """Aggregate table renders without raising exceptions."""
        console, buffer = _make_console()
        aggregate = _sample_aggregate()
        render_aggregate_table(aggregate, console=console)
        output = buffer.getvalue()
        assert len(output) > 0

    def test_displays_difficulty_and_count(self) -> None:
        """Output shows difficulty level and puzzle count."""
        console, buffer = _make_console()
        aggregate = _sample_aggregate()
        render_aggregate_table(aggregate, console=console)
        output = buffer.getvalue()
        assert "Medium" in output
        assert "10" in output

    def test_displays_mean_min_max(self) -> None:
        """Output includes mean/min/max formatting."""
        console, buffer = _make_console()
        aggregate = _sample_aggregate()
        render_aggregate_table(aggregate, console=console)
        output = buffer.getvalue()
        # Check that some statistics appear
        assert "90.0" in output  # Forward checking mean time (best)
        assert "60" in output  # Forward checking min time

    def test_displays_solve_rate(self) -> None:
        """Output includes solve rate percentage."""
        console, buffer = _make_console()
        aggregate = _sample_aggregate()
        render_aggregate_table(aggregate, console=console)
        output = buffer.getvalue()
        assert "100%" in output  # Backtracking and others have 100%
        assert "80%" in output  # SA has 80%

    def test_empty_stats_shows_message(self) -> None:
        """Empty stats dict shows a warning message."""
        console, buffer = _make_console()
        aggregate = AggregateStats(
            difficulty=DifficultyLevel.HARD,
            puzzle_count=0,
            stats={},
        )
        render_aggregate_table(aggregate, console=console)
        output = buffer.getvalue()
        assert "No aggregate" in output


class TestRenderPerformanceChart:
    """Tests for render_performance_chart function."""

    def test_renders_without_error(self) -> None:
        """Performance chart renders without exceptions."""
        console, buffer = _make_console()
        results = _sample_results()
        render_performance_chart(results, metric="states_explored", console=console)
        output = buffer.getvalue()
        assert len(output) > 0

    def test_displays_bar_characters(self) -> None:
        """Output contains bar chart characters."""
        console, buffer = _make_console()
        results = _sample_results()
        render_performance_chart(results, metric="states_explored", console=console)
        output = buffer.getvalue()
        assert "█" in output

    def test_displays_metric_label(self) -> None:
        """Output contains the metric name as a title."""
        console, buffer = _make_console()
        results = _sample_results()
        render_performance_chart(results, metric="time_ms", console=console)
        output = buffer.getvalue()
        assert "Time Ms" in output

    def test_displays_values(self) -> None:
        """Output includes numeric values alongside bars."""
        console, buffer = _make_console()
        results = _sample_results()
        render_performance_chart(results, metric="states_explored", console=console)
        output = buffer.getvalue()
        assert "5,000" in output
        assert "150" in output

    def test_empty_results_shows_message(self) -> None:
        """Empty results dict shows a warning message."""
        console, buffer = _make_console()
        render_performance_chart({}, metric="states_explored", console=console)
        output = buffer.getvalue()
        assert "No results" in output

    def test_all_zero_values_handles_gracefully(self) -> None:
        """All-zero metric values don't cause division by zero."""
        console, buffer = _make_console()
        results = {
            SolverType.BACKTRACKING: SolveResult(
                solver_type=SolverType.BACKTRACKING,
                status=SolveStatus.SOLVED,
                time_ms=0,
                states_explored=0,
                backtracks=0,
            ),
            SolverType.INFORMED: SolveResult(
                solver_type=SolverType.INFORMED,
                status=SolveStatus.SOLVED,
                time_ms=0,
                states_explored=0,
                backtracks=0,
            ),
        }
        render_performance_chart(results, metric="time_ms", console=console)
        output = buffer.getvalue()
        # Should not raise and should produce output
        assert len(output) > 0


class TestRenderGroupedByDifficulty:
    """Tests for render_grouped_by_difficulty function."""

    def test_renders_multiple_difficulties(self) -> None:
        """Groups and renders tables by difficulty level."""
        console, buffer = _make_console()
        comparison_easy = ComparisonTable(
            puzzle_id="easy-001",
            difficulty=DifficultyLevel.EASY,
            results=_sample_results(),
            rankings={"states_explored": list(_sample_results().keys())},
        )
        comparison_hard = ComparisonTable(
            puzzle_id="hard-001",
            difficulty=DifficultyLevel.HARD,
            results=_sample_results(),
            rankings={"states_explored": list(_sample_results().keys())},
        )
        grouped = {
            DifficultyLevel.EASY: [comparison_easy],
            DifficultyLevel.HARD: [comparison_hard],
        }
        render_grouped_by_difficulty(grouped, console=console)
        output = buffer.getvalue()
        assert "Easy" in output
        assert "Hard" in output
        assert "easy-001" in output
        assert "hard-001" in output

    def test_skips_empty_difficulties(self) -> None:
        """Doesn't render sections for difficulties with no data."""
        console, buffer = _make_console()
        render_grouped_by_difficulty({}, console=console)
        output = buffer.getvalue()
        # Should produce minimal output (no difficulty headers)
        assert "Easy" not in output
        assert "Medium" not in output


class TestRenderFullDashboard:
    """Tests for render_full_dashboard function."""

    def test_renders_full_dashboard(self) -> None:
        """Full dashboard renders all sections without error."""
        console, buffer = _make_console()
        comparisons = [_sample_comparison()]
        aggregates = {DifficultyLevel.MEDIUM: _sample_aggregate()}
        render_full_dashboard(comparisons, aggregates, console=console)
        output = buffer.getvalue()
        assert "Comparative Analysis Dashboard" in output
        assert "Aggregate Statistics" in output
        assert "Performance Chart" in output

    def test_empty_data_renders_gracefully(self) -> None:
        """Dashboard handles empty data without crashing."""
        console, buffer = _make_console()
        render_full_dashboard([], {}, console=console)
        output = buffer.getvalue()
        assert "Comparative Analysis Dashboard" in output
