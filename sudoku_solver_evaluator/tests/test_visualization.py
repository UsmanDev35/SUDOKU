"""Tests for the step-by-step visualization controller.

Tests cover the core functionality of VisualizationController including
step processing, delay clamping, state management, and grid rendering.
"""

from __future__ import annotations

from typing import Generator

import pytest

from sudoku_solver_evaluator.models.enums import (
    SolveStatus,
    SolverType,
    StepType,
)
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.ui.visualization import (
    DEFAULT_DELAY_MS,
    MAX_DELAY_MS,
    MIN_DELAY_MS,
    VisualizationController,
    clamp_delay,
    run_visualization,
)


# ---------- Fixtures ----------


def _make_empty_grid() -> Grid:
    """Create a simple grid with a few pre-filled cells for testing."""
    values = [[0] * 9 for _ in range(9)]
    # Set a few fixed cells
    values[0][0] = 5
    values[0][1] = 3
    values[1][0] = 6
    return Grid.from_2d_list(values)


def _make_step_generator(
    steps: list[StepEvent], result: SolveResult
) -> Generator[StepEvent, None, SolveResult]:
    """Create a generator that yields given steps and returns a result."""
    for step in steps:
        yield step
    return result


# ---------- Tests for clamp_delay ----------


class TestClampDelay:
    """Tests for the clamp_delay utility function."""

    def test_clamp_below_minimum(self) -> None:
        """Values below 100ms should be clamped to 100ms."""
        assert clamp_delay(50) == MIN_DELAY_MS
        assert clamp_delay(0) == MIN_DELAY_MS
        assert clamp_delay(-100) == MIN_DELAY_MS

    def test_clamp_above_maximum(self) -> None:
        """Values above 2000ms should be clamped to 2000ms."""
        assert clamp_delay(3000) == MAX_DELAY_MS
        assert clamp_delay(5000) == MAX_DELAY_MS

    def test_within_valid_range(self) -> None:
        """Values within range should be returned unchanged."""
        assert clamp_delay(100) == 100
        assert clamp_delay(500) == 500
        assert clamp_delay(1000) == 1000
        assert clamp_delay(2000) == 2000

    def test_boundary_values(self) -> None:
        """Exact boundary values should be valid."""
        assert clamp_delay(MIN_DELAY_MS) == MIN_DELAY_MS
        assert clamp_delay(MAX_DELAY_MS) == MAX_DELAY_MS


# ---------- Tests for VisualizationController initialization ----------


class TestVisualizationControllerInit:
    """Tests for VisualizationController initialization."""

    def test_default_delay(self) -> None:
        """Controller should use default delay of 500ms."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        assert controller.delay_ms == DEFAULT_DELAY_MS

    def test_custom_delay(self) -> None:
        """Controller should accept custom delay within valid range."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid, delay_ms=1000)
        assert controller.delay_ms == 1000

    def test_delay_clamped_below(self) -> None:
        """Controller should clamp delay below minimum."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid, delay_ms=50)
        assert controller.delay_ms == MIN_DELAY_MS

    def test_delay_clamped_above(self) -> None:
        """Controller should clamp delay above maximum."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid, delay_ms=5000)
        assert controller.delay_ms == MAX_DELAY_MS

    def test_initial_state(self) -> None:
        """Controller should start with zero metrics and unpaused."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        assert controller.states_explored == 0
        assert controller.backtracks == 0
        assert controller.is_paused is False
        assert controller.is_skipping is False
        assert controller.is_running is False

    def test_grid_is_copied(self) -> None:
        """Controller should work on a copy of the input grid."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        # Modify the controller's grid; original should be unchanged
        controller.grid.set_value(5, 5, 9)
        assert grid.get_cell(5, 5).value is None


# ---------- Tests for set_delay ----------


class TestSetDelay:
    """Tests for the set_delay method."""

    def test_set_valid_delay(self) -> None:
        """set_delay should update the delay when within range."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        controller.set_delay(750)
        assert controller.delay_ms == 750

    def test_set_delay_clamps(self) -> None:
        """set_delay should clamp values outside the valid range."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        controller.set_delay(50)
        assert controller.delay_ms == MIN_DELAY_MS
        controller.set_delay(9999)
        assert controller.delay_ms == MAX_DELAY_MS


# ---------- Tests for _process_step ----------


class TestProcessStep:
    """Tests for step event processing logic."""

    def test_process_assign_step(self) -> None:
        """ASSIGN step should update grid value and set highlight."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)

        event = StepEvent(
            step_type=StepType.ASSIGN,
            row=2,
            col=3,
            value=7,
            states_explored=1,
            backtracks=0,
        )
        controller._process_step(event)

        assert controller.grid.get_cell(2, 3).value == 7
        assert controller.states_explored == 1
        assert controller.backtracks == 0
        assert (2, 3) in controller._highlight_cells
        assert controller._is_backtrack is False
        assert controller._is_swap is False

    def test_process_backtrack_step(self) -> None:
        """BACKTRACK step should clear cell value and set backtrack flag."""
        grid = _make_empty_grid()
        # Pre-set a value so backtrack can clear it
        grid.set_value(2, 3, 7)
        controller = VisualizationController(grid)

        event = StepEvent(
            step_type=StepType.BACKTRACK,
            row=2,
            col=3,
            value=None,
            previous_value=7,
            states_explored=1,
            backtracks=1,
        )
        controller._process_step(event)

        assert controller.grid.get_cell(2, 3).value is None
        assert controller.backtracks == 1
        assert (2, 3) in controller._highlight_cells
        assert controller._is_backtrack is True
        assert controller._step_label == "BACKTRACK"

    def test_process_swap_step(self) -> None:
        """SWAP step should highlight both cells and set swap flag."""
        grid = _make_empty_grid()
        # Fill some values for swap
        grid.set_value(3, 0, 1)
        grid.set_value(3, 1, 2)
        controller = VisualizationController(grid)

        event = StepEvent(
            step_type=StepType.SWAP,
            row=3,
            col=0,
            swap_row=3,
            swap_col=1,
            states_explored=5,
            backtracks=0,
        )
        controller._process_step(event)

        # Both cells should be highlighted
        assert (3, 0) in controller._highlight_cells
        assert (3, 1) in controller._highlight_cells
        assert controller._is_swap is True
        assert controller._step_label == "SWAP"
        # Values should be swapped
        assert controller.grid.get_cell(3, 0).value == 2
        assert controller.grid.get_cell(3, 1).value == 1

    def test_process_propagate_step(self) -> None:
        """PROPAGATE step should assign value and highlight cell."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)

        event = StepEvent(
            step_type=StepType.PROPAGATE,
            row=4,
            col=4,
            value=9,
            states_explored=3,
            backtracks=0,
        )
        controller._process_step(event)

        assert controller.grid.get_cell(4, 4).value == 9
        assert (4, 4) in controller._highlight_cells
        assert "PROPAGATE" in controller._step_label

    def test_metrics_update_from_events(self) -> None:
        """Metrics should update from each event's running counters."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)

        # First event
        event1 = StepEvent(
            step_type=StepType.ASSIGN,
            row=0,
            col=2,
            value=4,
            states_explored=1,
            backtracks=0,
        )
        controller._process_step(event1)
        assert controller.states_explored == 1
        assert controller.backtracks == 0

        # Second event with higher metrics
        event2 = StepEvent(
            step_type=StepType.ASSIGN,
            row=0,
            col=3,
            value=6,
            states_explored=2,
            backtracks=0,
        )
        controller._process_step(event2)
        assert controller.states_explored == 2

        # Backtrack event
        event3 = StepEvent(
            step_type=StepType.BACKTRACK,
            row=0,
            col=3,
            previous_value=6,
            states_explored=2,
            backtracks=1,
        )
        controller._process_step(event3)
        assert controller.backtracks == 1


# ---------- Tests for pause/resume/skip controls ----------


class TestControls:
    """Tests for pause, resume, and skip controls."""

    def test_pause(self) -> None:
        """pause() should set is_paused to True."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        controller.pause()
        assert controller.is_paused is True

    def test_resume(self) -> None:
        """resume() should set is_paused to False."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        controller.pause()
        controller.resume()
        assert controller.is_paused is False

    def test_skip_to_end(self) -> None:
        """skip_to_end() should set is_skipping and clear is_paused."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        controller.pause()
        controller.skip_to_end()
        assert controller.is_skipping is True
        assert controller.is_paused is False


# ---------- Tests for run_visualization convenience function ----------


class TestRunVisualization:
    """Tests for the run_visualization convenience function."""

    def test_returns_solve_result(self) -> None:
        """run_visualization should return the SolveResult from the generator."""
        grid = _make_empty_grid()
        expected_result = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            solved_grid=grid,
            time_ms=100,
            states_explored=5,
            backtracks=2,
        )
        steps = [
            StepEvent(
                step_type=StepType.ASSIGN,
                row=0,
                col=2,
                value=4,
                states_explored=1,
                backtracks=0,
            ),
        ]
        gen = _make_step_generator(steps, expected_result)

        # Use skip mode to avoid actual delays
        controller = VisualizationController(grid, delay_ms=100)
        controller.is_skipping = True
        result = controller.run(gen)

        assert result is not None
        assert result.status == SolveStatus.SOLVED
        assert result.states_explored == 5

    def test_processes_all_steps(self) -> None:
        """Controller should process all steps from the generator."""
        grid = _make_empty_grid()
        expected_result = SolveResult(
            solver_type=SolverType.BACKTRACKING,
            status=SolveStatus.SOLVED,
            solved_grid=grid,
            time_ms=200,
            states_explored=3,
            backtracks=1,
        )
        steps = [
            StepEvent(
                step_type=StepType.ASSIGN,
                row=0,
                col=2,
                value=4,
                states_explored=1,
                backtracks=0,
            ),
            StepEvent(
                step_type=StepType.ASSIGN,
                row=0,
                col=3,
                value=6,
                states_explored=2,
                backtracks=0,
            ),
            StepEvent(
                step_type=StepType.BACKTRACK,
                row=0,
                col=3,
                previous_value=6,
                states_explored=2,
                backtracks=1,
            ),
            StepEvent(
                step_type=StepType.ASSIGN,
                row=0,
                col=3,
                value=8,
                states_explored=3,
                backtracks=1,
            ),
        ]
        gen = _make_step_generator(steps, expected_result)

        controller = VisualizationController(grid, delay_ms=100)
        controller.is_skipping = True  # Skip delays for testing
        result = controller.run(gen)

        assert result.status == SolveStatus.SOLVED
        # After processing all steps, metrics should reflect final step
        assert controller.states_explored == 3
        assert controller.backtracks == 1


# ---------- Tests for grid rendering ----------


class TestGridRendering:
    """Tests for grid text rendering."""

    def test_render_grid_text_returns_text(self) -> None:
        """_render_grid_text should return a Rich Text object."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        text = controller._render_grid_text()
        # Should be a Rich Text object
        assert hasattr(text, "plain")
        # Should contain the fixed cell values
        plain = text.plain
        assert "5" in plain
        assert "3" in plain
        assert "6" in plain

    def test_render_display_returns_panel(self) -> None:
        """_render_display should return a Rich Panel."""
        grid = _make_empty_grid()
        controller = VisualizationController(grid)
        panel = controller._render_display()
        assert panel is not None
        # Panel should have the expected title
        assert "Visualization" in str(panel.title)

    def test_backtrack_label_displayed(self) -> None:
        """BACKTRACK label should appear in the display after a backtrack step."""
        grid = _make_empty_grid()
        grid.set_value(2, 3, 7)
        controller = VisualizationController(grid)

        event = StepEvent(
            step_type=StepType.BACKTRACK,
            row=2,
            col=3,
            previous_value=7,
            states_explored=1,
            backtracks=1,
        )
        controller._process_step(event)
        assert controller._step_label == "BACKTRACK"
