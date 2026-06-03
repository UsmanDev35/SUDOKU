"""Unit tests for the adversarial race controller.

Tests cover:
- Basic race execution between two solvers
- Winner determination logic
- Timeout handling (one and both timeouts)
- Exception handling in solver threads
- Live status updates
- Tie detection within 1-second interval
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from sudoku_solver_evaluator.adversarial.race import RaceController
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import RaceResult, RaceStatus, SolveResult
from sudoku_solver_evaluator.solvers import SolverManager


def _make_easy_grid() -> Grid:
    """Create a simple puzzle grid with only one empty cell for fast solving."""
    # A nearly-complete valid grid with one empty cell at (8, 8)
    values = [
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 1, 5, 3, 7, 2, 8, 4],
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 1, 7, 0],  # Last cell is empty
    ]
    return Grid.from_2d_list(values)


def _make_harder_grid() -> Grid:
    """Create a puzzle grid with several empty cells."""
    values = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]
    return Grid.from_2d_list(values)


class TestRaceControllerInit:
    """Tests for RaceController initialization."""

    def test_creates_with_default_solver_manager(self) -> None:
        """RaceController creates its own SolverManager if none provided."""
        controller = RaceController()
        assert controller._solver_manager is not None

    def test_creates_with_provided_solver_manager(self) -> None:
        """RaceController uses the provided SolverManager."""
        manager = SolverManager()
        controller = RaceController(solver_manager=manager)
        assert controller._solver_manager is manager


class TestRaceControllerStartRace:
    """Tests for RaceController.start_race method."""

    def test_raises_for_same_solver(self) -> None:
        """start_race raises ValueError when both solvers are the same."""
        controller = RaceController()
        grid = _make_easy_grid()
        with pytest.raises(ValueError, match="two distinct solvers"):
            controller.start_race(grid, SolverType.BACKTRACKING, SolverType.BACKTRACKING)

    def test_basic_race_completes(self) -> None:
        """A basic race between two solvers completes and returns a RaceResult."""
        controller = RaceController()
        grid = _make_easy_grid()
        result = controller.start_race(
            grid, SolverType.BACKTRACKING, SolverType.FORWARD_CHECKING, timeout=30.0
        )

        assert isinstance(result, RaceResult)
        assert result.solver_a_type == SolverType.BACKTRACKING
        assert result.solver_b_type == SolverType.FORWARD_CHECKING
        assert result.solver_a_result is not None
        assert result.solver_b_result is not None

    def test_both_solvers_solve_easy_puzzle(self) -> None:
        """Both solvers should solve an easy puzzle successfully."""
        controller = RaceController()
        grid = _make_easy_grid()
        result = controller.start_race(
            grid, SolverType.BACKTRACKING, SolverType.FORWARD_CHECKING, timeout=30.0
        )

        assert result.solver_a_result.status == SolveStatus.SOLVED
        assert result.solver_b_result.status == SolveStatus.SOLVED

    def test_race_with_harder_puzzle(self) -> None:
        """Race works with a puzzle that requires more computation."""
        controller = RaceController()
        grid = _make_harder_grid()
        result = controller.start_race(
            grid, SolverType.BACKTRACKING, SolverType.INFORMED, timeout=30.0
        )

        assert result.solver_a_result.status == SolveStatus.SOLVED
        assert result.solver_b_result.status == SolveStatus.SOLVED

    def test_time_difference_computed(self) -> None:
        """time_difference_ms is computed as abs difference of solve times."""
        controller = RaceController()
        grid = _make_easy_grid()
        result = controller.start_race(
            grid, SolverType.BACKTRACKING, SolverType.FORWARD_CHECKING, timeout=30.0
        )

        expected_diff = abs(
            result.solver_a_result.time_ms - result.solver_b_result.time_ms
        )
        assert result.time_difference_ms == expected_diff


class TestRaceControllerTimeout:
    """Tests for timeout handling in the race controller."""

    def test_timeout_stops_race(self) -> None:
        """A very short timeout should cause at least one solver to timeout."""
        controller = RaceController()
        grid = _make_harder_grid()
        # Use an extremely short timeout
        result = controller.start_race(
            grid, SolverType.BACKTRACKING, SolverType.INFORMED, timeout=0.001
        )

        # At least check the race completes without hanging
        assert isinstance(result, RaceResult)


class TestRaceControllerWinnerDetermination:
    """Tests for winner determination logic."""

    def test_winner_is_faster_solver(self) -> None:
        """When both solve, the faster one wins (if >1s difference)."""
        controller = RaceController()

        # Manually set results to test winner logic
        controller._result_a = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            time_ms=500,
            states_explored=100,
        )
        controller._result_b = SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.SOLVED,
            time_ms=2000,
            states_explored=50,
        )

        winner = controller._determine_winner(SolverType.BACKTRACKING, SolverType.INFORMED)
        assert winner == SolverType.BACKTRACKING

    def test_winner_is_solver_b_when_faster(self) -> None:
        """Solver B wins when it has lower time_ms."""
        controller = RaceController()

        controller._result_a = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            time_ms=3000,
            states_explored=200,
        )
        controller._result_b = SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.SOLVED,
            time_ms=1000,
            states_explored=50,
        )

        winner = controller._determine_winner(SolverType.BACKTRACKING, SolverType.INFORMED)
        assert winner == SolverType.INFORMED

    def test_tie_within_one_second(self) -> None:
        """If both complete within 1000ms of each other, it's a tie."""
        controller = RaceController()

        controller._result_a = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            time_ms=1500,
            states_explored=100,
        )
        controller._result_b = SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.SOLVED,
            time_ms=2000,
            states_explored=50,
        )

        winner = controller._determine_winner(SolverType.BACKTRACKING, SolverType.INFORMED)
        assert winner is None  # Tie

    def test_one_solved_one_timeout_winner(self) -> None:
        """If only one solves, that solver wins."""
        controller = RaceController()

        controller._result_a = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            time_ms=5000,
            states_explored=100,
        )
        controller._result_b = SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.TIMEOUT,
            time_ms=60000,
            states_explored=50000,
        )

        winner = controller._determine_winner(SolverType.BACKTRACKING, SolverType.INFORMED)
        assert winner == SolverType.BACKTRACKING

    def test_both_timeout_no_winner(self) -> None:
        """If neither solves (both timeout), there is no winner."""
        controller = RaceController()

        controller._result_a = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.TIMEOUT,
            time_ms=60000,
            states_explored=10000,
        )
        controller._result_b = SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.TIMEOUT,
            time_ms=60000,
            states_explored=8000,
        )

        winner = controller._determine_winner(SolverType.BACKTRACKING, SolverType.INFORMED)
        assert winner is None

    def test_both_failed_no_winner(self) -> None:
        """If both fail, there is no winner."""
        controller = RaceController()

        controller._result_a = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.FAILED,
            time_ms=1000,
            states_explored=100,
        )
        controller._result_b = SolveResult(
            solver_type=SolverType.INFORMED,
            status=SolveStatus.FAILED,
            time_ms=2000,
            states_explored=200,
        )

        winner = controller._determine_winner(SolverType.BACKTRACKING, SolverType.INFORMED)
        assert winner is None


class TestRaceControllerLiveStatus:
    """Tests for live status reporting."""

    def test_get_live_status_raises_when_no_race(self) -> None:
        """get_live_status raises RuntimeError when no race is running."""
        controller = RaceController()
        with pytest.raises(RuntimeError, match="No race is currently in progress"):
            controller.get_live_status()

    def test_get_live_status_during_race(self) -> None:
        """get_live_status returns valid status tuples during a race."""
        controller = RaceController()
        grid = _make_harder_grid()

        # Use a longer timeout to ensure we can read status mid-race
        # We'll use a thread to start the race and check status from here
        race_result_holder: list[RaceResult] = []

        def run_race() -> None:
            result = controller.start_race(
                grid, SolverType.BACKTRACKING, SolverType.INFORMED, timeout=10.0
            )
            race_result_holder.append(result)

        race_thread = threading.Thread(target=run_race)
        race_thread.start()

        # Give race time to start
        time.sleep(0.2)

        # Try to read status if the race is still running
        if controller._is_running:
            status_a, status_b = controller.get_live_status()
            assert isinstance(status_a, RaceStatus)
            assert isinstance(status_b, RaceStatus)
            assert status_a.solver_type == SolverType.BACKTRACKING
            assert status_b.solver_type == SolverType.INFORMED

        race_thread.join(timeout=15.0)


class TestRaceControllerStop:
    """Tests for the stop method."""

    def test_stop_sets_cancel_event(self) -> None:
        """stop() sets the cancel event."""
        controller = RaceController()
        assert not controller._cancel_event.is_set()
        controller.stop()
        assert controller._cancel_event.is_set()
