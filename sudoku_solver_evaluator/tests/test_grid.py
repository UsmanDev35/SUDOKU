"""Unit tests for Grid and Cell data models.

Tests cover Cell creation, box property calculation, Grid construction,
querying methods, validation, copying, and edge cases.

Requirements: 1.1
"""

import pytest
from sudoku_solver_evaluator.models.grid import Cell, Grid


# --- Sample Data ---

# A known valid Sudoku puzzle (0 = empty)
SAMPLE_PUZZLE = [
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

# A fully solved valid Sudoku grid
SOLVED_GRID = [
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

# An empty grid (all zeros)
EMPTY_GRID = [[0] * 9 for _ in range(9)]


# --- Cell Tests ---


class TestCell:
    """Tests for Cell dataclass creation and properties."""

    def test_cell_creation_defaults(self):
        """Cell created with row/col has None value, not fixed, full domain."""
        cell = Cell(row=0, col=0)
        assert cell.row == 0
        assert cell.col == 0
        assert cell.value is None
        assert cell.is_fixed is False
        assert cell.domain == set(range(1, 10))

    def test_cell_creation_with_value(self):
        """Cell created with explicit value and is_fixed."""
        cell = Cell(row=3, col=5, value=7, is_fixed=True, domain={7})
        assert cell.row == 3
        assert cell.col == 5
        assert cell.value == 7
        assert cell.is_fixed is True
        assert cell.domain == {7}

    def test_cell_box_top_left_corner(self):
        """Cell at (0,0) is in box 0."""
        cell = Cell(row=0, col=0)
        assert cell.box == 0

    def test_cell_box_top_right_corner(self):
        """Cell at (0,8) is in box 2."""
        cell = Cell(row=0, col=8)
        assert cell.box == 2

    def test_cell_box_bottom_left_corner(self):
        """Cell at (8,0) is in box 6."""
        cell = Cell(row=8, col=0)
        assert cell.box == 6

    def test_cell_box_bottom_right_corner(self):
        """Cell at (8,8) is in box 8."""
        cell = Cell(row=8, col=8)
        assert cell.box == 8

    def test_cell_box_center(self):
        """Cell at (4,4) is in box 4 (center of grid)."""
        cell = Cell(row=4, col=4)
        assert cell.box == 4

    def test_cell_box_edges(self):
        """Cells on box boundaries map correctly."""
        # (2,2) is last cell of box 0
        assert Cell(row=2, col=2).box == 0
        # (3,0) is first cell of box 3
        assert Cell(row=3, col=0).box == 3
        # (0,3) is first cell of box 1
        assert Cell(row=0, col=3).box == 1
        # (5,5) is last cell of box 4
        assert Cell(row=5, col=5).box == 4

    def test_cell_box_all_positions(self):
        """Every cell maps to the correct box index."""
        expected_boxes = [
            [0, 0, 0, 1, 1, 1, 2, 2, 2],
            [0, 0, 0, 1, 1, 1, 2, 2, 2],
            [0, 0, 0, 1, 1, 1, 2, 2, 2],
            [3, 3, 3, 4, 4, 4, 5, 5, 5],
            [3, 3, 3, 4, 4, 4, 5, 5, 5],
            [3, 3, 3, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 7, 7, 7, 8, 8, 8],
            [6, 6, 6, 7, 7, 7, 8, 8, 8],
            [6, 6, 6, 7, 7, 7, 8, 8, 8],
        ]
        for r in range(9):
            for c in range(9):
                cell = Cell(row=r, col=c)
                assert cell.box == expected_boxes[r][c], f"Cell({r},{c}) box mismatch"


# --- Grid Tests ---


class TestGridFromList:
    """Tests for Grid.from_2d_list construction."""

    def test_from_2d_list_creates_grid(self):
        """Grid.from_2d_list creates a valid 9x9 grid from a puzzle."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        assert len(grid.cells) == 9
        assert all(len(row) == 9 for row in grid.cells)

    def test_from_2d_list_fixed_cells(self):
        """Non-zero values become fixed cells with correct value."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        # (0,0) = 5, should be fixed
        cell = grid.get_cell(0, 0)
        assert cell.value == 5
        assert cell.is_fixed is True
        assert cell.domain == {5}

    def test_from_2d_list_empty_cells(self):
        """Zero values become empty cells with None value and full domain."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        # (0,2) = 0, should be empty
        cell = grid.get_cell(0, 2)
        assert cell.value is None
        assert cell.is_fixed is False
        assert cell.domain == set(range(1, 10))

    def test_from_2d_list_cell_positions(self):
        """All cells have correct row and col attributes."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        for r in range(9):
            for c in range(9):
                cell = grid.get_cell(r, c)
                assert cell.row == r
                assert cell.col == c


class TestGridGetRow:
    """Tests for Grid.get_row."""

    def test_get_row_returns_9_cells(self):
        """get_row returns exactly 9 cells."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        row = grid.get_row(0)
        assert len(row) == 9

    def test_get_row_correct_values(self):
        """get_row returns cells with correct values for row 0."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        row = grid.get_row(0)
        values = [cell.value for cell in row]
        expected = [5, 3, None, None, 7, None, None, None, None]
        assert values == expected

    def test_get_row_all_same_row_index(self):
        """All cells in get_row have the same row index."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        for r in range(9):
            row = grid.get_row(r)
            assert all(cell.row == r for cell in row)


class TestGridGetCol:
    """Tests for Grid.get_col."""

    def test_get_col_returns_9_cells(self):
        """get_col returns exactly 9 cells."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        col = grid.get_col(0)
        assert len(col) == 9

    def test_get_col_correct_values(self):
        """get_col returns cells with correct values for column 0."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        col = grid.get_col(0)
        values = [cell.value for cell in col]
        expected = [5, 6, None, 8, 4, 7, None, None, None]
        assert values == expected

    def test_get_col_all_same_col_index(self):
        """All cells in get_col have the same col index."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        for c in range(9):
            col = grid.get_col(c)
            assert all(cell.col == c for cell in col)


class TestGridGetBox:
    """Tests for Grid.get_box."""

    def test_get_box_returns_9_cells(self):
        """get_box returns exactly 9 cells."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        box = grid.get_box(0)
        assert len(box) == 9

    def test_get_box_0_correct_cells(self):
        """Box 0 contains cells from rows 0-2, cols 0-2."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        box = grid.get_box(0)
        positions = [(cell.row, cell.col) for cell in box]
        expected = [(r, c) for r in range(3) for c in range(3)]
        assert positions == expected

    def test_get_box_4_center(self):
        """Box 4 (center) contains cells from rows 3-5, cols 3-5."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        box = grid.get_box(4)
        positions = [(cell.row, cell.col) for cell in box]
        expected = [(r, c) for r in range(3, 6) for c in range(3, 6)]
        assert positions == expected

    def test_get_box_8_bottom_right(self):
        """Box 8 (bottom-right) contains cells from rows 6-8, cols 6-8."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        box = grid.get_box(8)
        positions = [(cell.row, cell.col) for cell in box]
        expected = [(r, c) for r in range(6, 9) for c in range(6, 9)]
        assert positions == expected

    def test_get_box_all_boxes_cover_grid(self):
        """All 9 boxes together cover all 81 cells exactly once."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        all_positions = set()
        for box_idx in range(9):
            box = grid.get_box(box_idx)
            for cell in box:
                all_positions.add((cell.row, cell.col))
        assert len(all_positions) == 81


class TestGridGetPeers:
    """Tests for Grid.get_peers."""

    def test_get_peers_count(self):
        """get_peers returns exactly 20 unique cells for any position."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(0, 0)
        assert len(peers) == 20

    def test_get_peers_count_center(self):
        """get_peers returns 20 cells for center position (4,4)."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(4, 4)
        assert len(peers) == 20

    def test_get_peers_excludes_self(self):
        """get_peers does not include the cell itself."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(4, 4)
        positions = [(cell.row, cell.col) for cell in peers]
        assert (4, 4) not in positions

    def test_get_peers_includes_row(self):
        """get_peers includes all cells in the same row (except self)."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(0, 0)
        peer_positions = {(cell.row, cell.col) for cell in peers}
        for c in range(1, 9):
            assert (0, c) in peer_positions

    def test_get_peers_includes_col(self):
        """get_peers includes all cells in the same column (except self)."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(0, 0)
        peer_positions = {(cell.row, cell.col) for cell in peers}
        for r in range(1, 9):
            assert (r, 0) in peer_positions

    def test_get_peers_includes_box(self):
        """get_peers includes all cells in the same box (except self)."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(0, 0)
        peer_positions = {(cell.row, cell.col) for cell in peers}
        # Box 0: rows 0-2, cols 0-2
        for r in range(3):
            for c in range(3):
                if (r, c) != (0, 0):
                    assert (r, c) in peer_positions

    def test_get_peers_unique(self):
        """get_peers returns unique cells (no duplicates)."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        peers = grid.get_peers(4, 4)
        positions = [(cell.row, cell.col) for cell in peers]
        assert len(positions) == len(set(positions))


class TestGridIsValid:
    """Tests for Grid.is_valid."""

    def test_is_valid_sample_puzzle(self):
        """A known valid puzzle returns True."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        assert grid.is_valid() is True

    def test_is_valid_solved_grid(self):
        """A fully solved valid grid returns True."""
        grid = Grid.from_2d_list(SOLVED_GRID)
        assert grid.is_valid() is True

    def test_is_valid_empty_grid(self):
        """An empty grid (all None) is valid (no duplicates)."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        assert grid.is_valid() is True

    def test_is_valid_row_duplicate(self):
        """Grid with duplicate in a row returns False."""
        invalid = [row[:] for row in EMPTY_GRID]
        invalid[0][0] = 5
        invalid[0][1] = 5  # duplicate in row 0
        grid = Grid.from_2d_list(invalid)
        assert grid.is_valid() is False

    def test_is_valid_col_duplicate(self):
        """Grid with duplicate in a column returns False."""
        invalid = [row[:] for row in EMPTY_GRID]
        invalid[0][0] = 3
        invalid[1][0] = 3  # duplicate in col 0
        grid = Grid.from_2d_list(invalid)
        assert grid.is_valid() is False

    def test_is_valid_box_duplicate(self):
        """Grid with duplicate in a box returns False."""
        invalid = [row[:] for row in EMPTY_GRID]
        invalid[0][0] = 9
        invalid[1][1] = 9  # duplicate in box 0
        grid = Grid.from_2d_list(invalid)
        assert grid.is_valid() is False


class TestGridIsComplete:
    """Tests for Grid.is_complete."""

    def test_is_complete_solved_grid(self):
        """A fully filled grid returns True."""
        grid = Grid.from_2d_list(SOLVED_GRID)
        assert grid.is_complete() is True

    def test_is_complete_empty_grid(self):
        """An empty grid returns False."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        assert grid.is_complete() is False

    def test_is_complete_partial_grid(self):
        """A partially filled grid returns False."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        assert grid.is_complete() is False

    def test_is_complete_single_empty_cell(self):
        """A grid with only one empty cell returns False."""
        almost_full = [row[:] for row in SOLVED_GRID]
        almost_full[8][8] = 0  # one empty cell
        grid = Grid.from_2d_list(almost_full)
        assert grid.is_complete() is False


class TestGridCopy:
    """Tests for Grid.copy."""

    def test_copy_creates_independent_grid(self):
        """Modifying a copy does not affect the original."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        grid_copy = grid.copy()

        # Modify the copy
        grid_copy.set_value(0, 2, 4)

        # Original should be unchanged
        assert grid.get_cell(0, 2).value is None
        assert grid_copy.get_cell(0, 2).value == 4

    def test_copy_preserves_values(self):
        """Copy has the same values as the original."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        grid_copy = grid.copy()

        for r in range(9):
            for c in range(9):
                assert grid.get_cell(r, c).value == grid_copy.get_cell(r, c).value

    def test_copy_preserves_fixed_status(self):
        """Copy preserves is_fixed status of all cells."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        grid_copy = grid.copy()

        for r in range(9):
            for c in range(9):
                assert grid.get_cell(r, c).is_fixed == grid_copy.get_cell(r, c).is_fixed

    def test_copy_domain_independence(self):
        """Modifying domain in copy does not affect original."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        grid_copy = grid.copy()

        # Modify domain in copy
        grid_copy.get_cell(0, 2).domain = {1, 2}

        # Original domain should be unchanged
        assert grid.get_cell(0, 2).domain == set(range(1, 10))


class TestGridCountFilled:
    """Tests for Grid.count_filled."""

    def test_count_filled_empty_grid(self):
        """Empty grid has 0 filled cells."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        assert grid.count_filled() == 0

    def test_count_filled_solved_grid(self):
        """Fully solved grid has 81 filled cells."""
        grid = Grid.from_2d_list(SOLVED_GRID)
        assert grid.count_filled() == 81

    def test_count_filled_sample_puzzle(self):
        """Sample puzzle has correct number of filled cells."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        expected = sum(1 for row in SAMPLE_PUZZLE for val in row if val != 0)
        assert grid.count_filled() == expected


class TestGridTo2dList:
    """Tests for Grid.to_2d_list and round-trip with from_2d_list."""

    def test_to_2d_list_round_trip(self):
        """from_2d_list followed by to_2d_list returns the original data."""
        grid = Grid.from_2d_list(SAMPLE_PUZZLE)
        result = grid.to_2d_list()
        assert result == SAMPLE_PUZZLE

    def test_to_2d_list_empty_grid(self):
        """Empty grid round-trips correctly."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        result = grid.to_2d_list()
        assert result == EMPTY_GRID

    def test_to_2d_list_solved_grid(self):
        """Solved grid round-trips correctly."""
        grid = Grid.from_2d_list(SOLVED_GRID)
        result = grid.to_2d_list()
        assert result == SOLVED_GRID


class TestGridEdgeCases:
    """Edge case tests for Grid."""

    def test_empty_grid_is_valid(self):
        """An all-empty grid is valid (no constraint violations)."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        assert grid.is_valid() is True

    def test_empty_grid_not_complete(self):
        """An all-empty grid is not complete."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        assert grid.is_complete() is False

    def test_empty_grid_get_empty_cells(self):
        """An all-empty grid has 81 empty cells."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        assert len(grid.get_empty_cells()) == 81

    def test_solved_grid_no_empty_cells(self):
        """A fully solved grid has 0 empty cells."""
        grid = Grid.from_2d_list(SOLVED_GRID)
        assert len(grid.get_empty_cells()) == 0

    def test_single_empty_cell(self):
        """Grid with single empty cell: 80 filled, 1 empty, not complete."""
        almost_full = [row[:] for row in SOLVED_GRID]
        almost_full[4][4] = 0
        grid = Grid.from_2d_list(almost_full)

        assert grid.count_filled() == 80
        assert grid.is_complete() is False
        assert len(grid.get_empty_cells()) == 1
        assert grid.get_empty_cells()[0].row == 4
        assert grid.get_empty_cells()[0].col == 4

    def test_set_and_clear_value(self):
        """set_value and clear_value work correctly."""
        grid = Grid.from_2d_list(EMPTY_GRID)
        grid.set_value(0, 0, 5)
        assert grid.get_cell(0, 0).value == 5

        grid.clear_value(0, 0)
        assert grid.get_cell(0, 0).value is None

    def test_fully_filled_valid_grid(self):
        """A fully filled valid grid is both valid and complete."""
        grid = Grid.from_2d_list(SOLVED_GRID)
        assert grid.is_valid() is True
        assert grid.is_complete() is True
