"""Grid and Cell data models for the Sudoku Solver and Evaluator system.

This module defines the core data structures representing a 9x9 Sudoku grid
and its individual cells. The Grid class provides methods for querying,
modifying, and validating the puzzle state.
"""

from dataclasses import dataclass, field
from typing import Optional
import copy


@dataclass
class Cell:
    """A single cell in the Sudoku grid.

    Attributes:
        row: Row index (0-8).
        col: Column index (0-8).
        value: The cell's current value (1-9), or None if empty.
        is_fixed: True if the cell is pre-filled and cannot be modified by solvers.
        domain: The set of possible values this cell can take given current constraints.
    """

    row: int
    col: int
    value: Optional[int] = None
    is_fixed: bool = False
    domain: set[int] = field(default_factory=lambda: set(range(1, 10)))

    @property
    def box(self) -> int:
        """Returns the 3x3 box index (0-8) for this cell.

        Boxes are numbered left-to-right, top-to-bottom:
        0 1 2
        3 4 5
        6 7 8
        """
        return (self.row // 3) * 3 + (self.col // 3)


@dataclass
class Grid:
    """9x9 Sudoku grid composed of Cell objects.

    Attributes:
        cells: A 9x9 matrix (list of lists) of Cell objects.
    """

    cells: list[list[Cell]]

    def get_cell(self, row: int, col: int) -> Cell:
        """Get the cell at the specified row and column.

        Args:
            row: Row index (0-8).
            col: Column index (0-8).

        Returns:
            The Cell at the given position.
        """
        return self.cells[row][col]

    def set_value(self, row: int, col: int, value: int) -> None:
        """Set the value of a cell.

        Args:
            row: Row index (0-8).
            col: Column index (0-8).
            value: The value to assign (1-9).
        """
        self.cells[row][col].value = value

    def clear_value(self, row: int, col: int) -> None:
        """Clear the value of a cell (set to None).

        Args:
            row: Row index (0-8).
            col: Column index (0-8).
        """
        self.cells[row][col].value = None

    def get_row(self, row: int) -> list[Cell]:
        """Get all cells in the specified row.

        Args:
            row: Row index (0-8).

        Returns:
            List of 9 Cell objects in the row.
        """
        return self.cells[row]

    def get_col(self, col: int) -> list[Cell]:
        """Get all cells in the specified column.

        Args:
            col: Column index (0-8).

        Returns:
            List of 9 Cell objects in the column.
        """
        return [self.cells[row][col] for row in range(9)]

    def get_box(self, box_index: int) -> list[Cell]:
        """Get all cells in the specified 3x3 box.

        Args:
            box_index: Box index (0-8), numbered left-to-right, top-to-bottom.

        Returns:
            List of 9 Cell objects in the box.
        """
        start_row = (box_index // 3) * 3
        start_col = (box_index % 3) * 3
        cells = []
        for r in range(start_row, start_row + 3):
            for c in range(start_col, start_col + 3):
                cells.append(self.cells[r][c])
        return cells

    def get_peers(self, row: int, col: int) -> list[Cell]:
        """Get all peer cells (same row, column, or box) excluding the cell itself.

        Args:
            row: Row index (0-8).
            col: Column index (0-8).

        Returns:
            List of unique Cell objects that share a row, column, or box
            with the specified cell (excluding the cell itself).
        """
        peers: set[tuple[int, int]] = set()

        # Same row
        for c in range(9):
            if c != col:
                peers.add((row, c))

        # Same column
        for r in range(9):
            if r != row:
                peers.add((r, col))

        # Same box
        box_start_row = (row // 3) * 3
        box_start_col = (col // 3) * 3
        for r in range(box_start_row, box_start_row + 3):
            for c in range(box_start_col, box_start_col + 3):
                if (r, c) != (row, col):
                    peers.add((r, c))

        return [self.cells[r][c] for r, c in peers]

    def get_empty_cells(self) -> list[Cell]:
        """Get all cells that do not have a value assigned.

        Returns:
            List of Cell objects where value is None.
        """
        empty = []
        for row in self.cells:
            for cell in row:
                if cell.value is None:
                    empty.append(cell)
        return empty

    def is_complete(self) -> bool:
        """Check if all cells in the grid have a value assigned.

        Returns:
            True if all 81 cells have a non-None value.
        """
        for row in self.cells:
            for cell in row:
                if cell.value is None:
                    return False
        return True

    def is_valid(self) -> bool:
        """Check if the grid has no constraint violations.

        Validates that no row, column, or 3x3 box contains duplicate
        non-zero values. Empty cells (None) are ignored.

        Returns:
            True if no duplicates exist in any row, column, or box.
        """
        # Check rows
        for row in range(9):
            if not self._is_unit_valid(self.get_row(row)):
                return False

        # Check columns
        for col in range(9):
            if not self._is_unit_valid(self.get_col(col)):
                return False

        # Check boxes
        for box in range(9):
            if not self._is_unit_valid(self.get_box(box)):
                return False

        return True

    def _is_unit_valid(self, cells: list[Cell]) -> bool:
        """Check if a unit (row, column, or box) has no duplicate values.

        Args:
            cells: List of cells in the unit.

        Returns:
            True if no duplicate non-None values exist.
        """
        values = [cell.value for cell in cells if cell.value is not None]
        return len(values) == len(set(values))

    def copy(self) -> "Grid":
        """Create a deep copy of this grid.

        Returns:
            A new Grid instance with independent Cell objects.
        """
        new_cells = []
        for row in self.cells:
            new_row = []
            for cell in row:
                new_cell = Cell(
                    row=cell.row,
                    col=cell.col,
                    value=cell.value,
                    is_fixed=cell.is_fixed,
                    domain=set(cell.domain),
                )
                new_row.append(new_cell)
            new_cells.append(new_row)
        return Grid(cells=new_cells)

    def count_filled(self) -> int:
        """Count the number of cells that have a value assigned.

        Returns:
            Integer count of cells with non-None values.
        """
        count = 0
        for row in self.cells:
            for cell in row:
                if cell.value is not None:
                    count += 1
        return count

    @classmethod
    def from_2d_list(cls, values: list[list[int]]) -> "Grid":
        """Create a Grid from a 2D list of integers.

        Values of 0 are treated as empty cells. Non-zero values are
        marked as fixed (pre-filled) cells.

        Args:
            values: A 9x9 list of integers where 0 represents empty cells
                    and 1-9 represent pre-filled values.

        Returns:
            A new Grid instance populated from the input values.
        """
        cells = []
        for row in range(9):
            cell_row = []
            for col in range(9):
                val = values[row][col]
                if val == 0:
                    cell = Cell(row=row, col=col, value=None, is_fixed=False)
                else:
                    cell = Cell(
                        row=row,
                        col=col,
                        value=val,
                        is_fixed=True,
                        domain={val},
                    )
                cell_row.append(cell)
            cells.append(cell_row)
        return cls(cells=cells)

    def to_2d_list(self) -> list[list[int]]:
        """Export the grid as a 2D list of integers.

        Empty cells (None) are represented as 0.

        Returns:
            A 9x9 list of integers where 0 represents empty cells.
        """
        result = []
        for row in self.cells:
            result.append([cell.value if cell.value is not None else 0 for cell in row])
        return result
