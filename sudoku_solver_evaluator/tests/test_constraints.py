"""Unit tests for constraint validation utilities.

Tests the functions in constraints/validator.py to ensure correct detection
of row, column, and box conflicts in Sudoku grids.
"""

import pytest

from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.constraints.validator import (
    has_row_conflict,
    has_col_conflict,
    has_box_conflict,
    is_valid_assignment,
    get_conflicts,
    is_grid_valid,
)


# --- Fixtures ---


@pytest.fixture
def empty_grid() -> Grid:
    """A completely empty 9x9 grid."""
    return Grid.from_2d_list([[0] * 9 for _ in range(9)])


@pytest.fixture
def valid_partial_grid() -> Grid:
    """A partially filled valid grid (no constraint violations)."""
    data = [[0] * 9 for _ in range(9)]
    # Place some values that don't conflict
    data[0][0] = 1
    data[0][1] = 2
    data[0][2] = 3
    data[1][3] = 4
    data[2][6] = 7
    data[4][4] = 5
    data[8][8] = 9
    return Grid.from_2d_list(data)


@pytest.fixture
def invalid_grid_row_dup() -> Grid:
    """A grid with a duplicate value in row 0."""
    data = [[0] * 9 for _ in range(9)]
    data[0][0] = 5
    data[0][7] = 5  # duplicate in same row
    return Grid.from_2d_list(data)


@pytest.fixture
def complete_valid_grid() -> Grid:
    """A fully solved valid Sudoku grid."""
    data = [
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 1, 5, 3, 7, 2, 8, 4],
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 1, 7, 9],
    ]
    return Grid.from_2d_list(data)


# --- has_row_conflict tests ---


class TestHasRowConflict:
    def test_no_conflict_empty_grid(self, empty_grid: Grid):
        assert has_row_conflict(empty_grid, 0, 0, 5) is False

    def test_conflict_exists_in_row(self, empty_grid: Grid):
        empty_grid.set_value(0, 3, 7)
        assert has_row_conflict(empty_grid, 0, 0, 7) is True

    def test_no_conflict_different_value(self, empty_grid: Grid):
        empty_grid.set_value(0, 3, 7)
        assert has_row_conflict(empty_grid, 0, 0, 8) is False

    def test_excludes_self(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        # Checking the cell itself should not report a conflict
        assert has_row_conflict(empty_grid, 0, 0, 5) is False


# --- has_col_conflict tests ---


class TestHasColConflict:
    def test_no_conflict_empty_grid(self, empty_grid: Grid):
        assert has_col_conflict(empty_grid, 0, 0, 5) is False

    def test_conflict_exists_in_col(self, empty_grid: Grid):
        empty_grid.set_value(5, 0, 3)
        assert has_col_conflict(empty_grid, 0, 0, 3) is True

    def test_no_conflict_different_value(self, empty_grid: Grid):
        empty_grid.set_value(5, 0, 3)
        assert has_col_conflict(empty_grid, 0, 0, 4) is False

    def test_excludes_self(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        assert has_col_conflict(empty_grid, 0, 0, 5) is False


# --- has_box_conflict tests ---


class TestHasBoxConflict:
    def test_no_conflict_empty_grid(self, empty_grid: Grid):
        assert has_box_conflict(empty_grid, 0, 0, 5) is False

    def test_conflict_in_same_box(self, empty_grid: Grid):
        empty_grid.set_value(1, 1, 9)
        # (0,0) is in the same box as (1,1)
        assert has_box_conflict(empty_grid, 0, 0, 9) is True

    def test_no_conflict_different_box(self, empty_grid: Grid):
        empty_grid.set_value(0, 3, 9)  # different box
        assert has_box_conflict(empty_grid, 0, 0, 9) is False

    def test_excludes_self(self, empty_grid: Grid):
        empty_grid.set_value(1, 1, 4)
        assert has_box_conflict(empty_grid, 1, 1, 4) is False

    def test_box_boundary(self, empty_grid: Grid):
        # (2,2) and (3,3) are in different boxes
        empty_grid.set_value(2, 2, 6)
        assert has_box_conflict(empty_grid, 3, 3, 6) is False


# --- is_valid_assignment tests ---


class TestIsValidAssignment:
    def test_valid_on_empty_grid(self, empty_grid: Grid):
        assert is_valid_assignment(empty_grid, 4, 4, 5) is True

    def test_invalid_row_conflict(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        assert is_valid_assignment(empty_grid, 0, 8, 5) is False

    def test_invalid_col_conflict(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        assert is_valid_assignment(empty_grid, 8, 0, 5) is False

    def test_invalid_box_conflict(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        assert is_valid_assignment(empty_grid, 2, 2, 5) is False

    def test_valid_no_conflicts(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        # (4, 4) is in a different row, col, and box
        assert is_valid_assignment(empty_grid, 4, 4, 5) is True


# --- get_conflicts tests ---


class TestGetConflicts:
    def test_empty_cell_returns_empty(self, empty_grid: Grid):
        assert get_conflicts(empty_grid, 0, 0) == []

    def test_no_conflicts(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        assert get_conflicts(empty_grid, 0, 0) == []

    def test_row_conflict_detected(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        empty_grid.set_value(0, 5, 5)
        conflicts = get_conflicts(empty_grid, 0, 0)
        assert (0, 5) in conflicts

    def test_col_conflict_detected(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        empty_grid.set_value(7, 0, 5)
        conflicts = get_conflicts(empty_grid, 0, 0)
        assert (7, 0) in conflicts

    def test_box_conflict_detected(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        empty_grid.set_value(2, 2, 5)
        conflicts = get_conflicts(empty_grid, 0, 0)
        assert (2, 2) in conflicts

    def test_multiple_conflicts(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 5)
        empty_grid.set_value(0, 5, 5)  # row conflict
        empty_grid.set_value(7, 0, 5)  # col conflict
        empty_grid.set_value(2, 2, 5)  # box conflict
        conflicts = get_conflicts(empty_grid, 0, 0)
        assert len(conflicts) == 3
        assert (0, 5) in conflicts
        assert (7, 0) in conflicts
        assert (2, 2) in conflicts

    def test_no_duplicate_entries(self, empty_grid: Grid):
        # A cell in the same row AND same box should only appear once
        empty_grid.set_value(0, 0, 5)
        empty_grid.set_value(0, 1, 5)  # same row AND same box
        conflicts = get_conflicts(empty_grid, 0, 0)
        assert conflicts.count((0, 1)) == 1


# --- is_grid_valid tests ---


class TestIsGridValid:
    def test_empty_grid_is_valid(self, empty_grid: Grid):
        assert is_grid_valid(empty_grid) is True

    def test_valid_partial_grid(self, valid_partial_grid: Grid):
        assert is_grid_valid(valid_partial_grid) is True

    def test_complete_valid_grid(self, complete_valid_grid: Grid):
        assert is_grid_valid(complete_valid_grid) is True

    def test_row_duplicate_invalid(self, invalid_grid_row_dup: Grid):
        assert is_grid_valid(invalid_grid_row_dup) is False

    def test_col_duplicate_invalid(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 3)
        empty_grid.set_value(5, 0, 3)
        assert is_grid_valid(empty_grid) is False

    def test_box_duplicate_invalid(self, empty_grid: Grid):
        empty_grid.set_value(0, 0, 8)
        empty_grid.set_value(2, 2, 8)
        assert is_grid_valid(empty_grid) is False
