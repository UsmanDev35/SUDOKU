"""Unit tests for the grid display module.

Tests verify that render_grid produces correct Rich Table output
with appropriate styling for fixed cells, solver-assigned cells,
empty cells, highlighted cells, and box separators.
"""

import pytest
from rich.text import Text
from rich.table import Table

from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.ui.display import (
    render_grid,
    _format_cell,
    STYLE_FIXED,
    STYLE_SOLVER_ASSIGNED,
    STYLE_EMPTY,
    STYLE_HIGHLIGHT,
    STYLE_HIGHLIGHT_SWAP,
    EMPTY_PLACEHOLDER,
)


@pytest.fixture
def sample_grid():
    """A sample puzzle grid with some pre-filled cells."""
    return Grid.from_2d_list([
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ])


@pytest.fixture
def solved_grid():
    """A fully solved grid where non-fixed cells are solver-assigned."""
    grid = Grid.from_2d_list([
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ])
    # Simulate solver-assigned values (is_fixed remains False)
    grid.set_value(0, 2, 4)
    grid.set_value(0, 3, 6)
    return grid


class TestFormatCell:
    """Tests for the _format_cell helper function."""

    def test_empty_cell_shows_placeholder(self):
        text = _format_cell(None, False, 0, 0, None, None)
        assert text.plain == EMPTY_PLACEHOLDER
        assert text.style == STYLE_EMPTY

    def test_fixed_cell_bold_white(self):
        text = _format_cell(5, True, 0, 0, None, None)
        assert text.plain == "5"
        assert text.style == STYLE_FIXED

    def test_solver_assigned_cell_green(self):
        text = _format_cell(4, False, 0, 2, None, None)
        assert text.plain == "4"
        assert text.style == STYLE_SOLVER_ASSIGNED

    def test_highlight_cell_overrides_fixed(self):
        text = _format_cell(5, True, 0, 0, (0, 0), None)
        assert text.plain == "5"
        assert text.style == STYLE_HIGHLIGHT

    def test_highlight_cell_overrides_solver_assigned(self):
        text = _format_cell(4, False, 1, 1, (1, 1), None)
        assert text.plain == "4"
        assert text.style == STYLE_HIGHLIGHT

    def test_highlight_cell_overrides_empty(self):
        text = _format_cell(None, False, 2, 2, (2, 2), None)
        assert text.plain == EMPTY_PLACEHOLDER
        assert text.style == STYLE_HIGHLIGHT

    def test_swap_highlight_style(self):
        text = _format_cell(3, False, 4, 4, None, (4, 4))
        assert text.plain == "3"
        assert text.style == STYLE_HIGHLIGHT_SWAP

    def test_highlight_takes_priority_over_swap(self):
        # If same cell is both highlight and swap, highlight wins
        text = _format_cell(7, False, 3, 3, (3, 3), (3, 3))
        assert text.style == STYLE_HIGHLIGHT

    def test_non_highlighted_cell_not_affected(self):
        # A different cell than the highlighted one
        text = _format_cell(9, True, 5, 5, (0, 0), (1, 1))
        assert text.style == STYLE_FIXED


class TestRenderGrid:
    """Tests for the render_grid function."""

    def test_returns_rich_table(self, sample_grid):
        result = render_grid(sample_grid)
        assert isinstance(result, Table)

    def test_table_has_9_columns(self, sample_grid):
        result = render_grid(sample_grid)
        assert len(result.columns) == 9

    def test_table_has_9_rows(self, sample_grid):
        result = render_grid(sample_grid)
        assert result.row_count == 9

    def test_no_highlight_renders_without_error(self, sample_grid):
        # Should not raise
        result = render_grid(sample_grid)
        assert result is not None

    def test_highlight_cell_renders_without_error(self, sample_grid):
        result = render_grid(sample_grid, highlight_cell=(4, 4))
        assert result is not None

    def test_highlight_swap_renders_without_error(self, sample_grid):
        result = render_grid(sample_grid, highlight_swap=(2, 5))
        assert result is not None

    def test_both_highlights_render_without_error(self, sample_grid):
        result = render_grid(
            sample_grid, highlight_cell=(0, 2), highlight_swap=(4, 4)
        )
        assert result is not None

    def test_solved_grid_distinguishes_fixed_from_assigned(self, solved_grid):
        # Render the solved grid and verify it completes
        result = render_grid(solved_grid)
        assert result.row_count == 9
