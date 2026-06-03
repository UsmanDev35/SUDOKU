"""Constraint validation utilities for Sudoku grids.

This module provides functions to check Sudoku constraints (row, column, and
3x3 box uniqueness) and detect conflicts. These utilities are used by solvers
to validate assignments and by the evaluator to verify solutions.

Sudoku Rules:
    - Each row must contain the digits 1-9 with no duplicates.
    - Each column must contain the digits 1-9 with no duplicates.
    - Each 3x3 box must contain the digits 1-9 with no duplicates.

Validates: Requirements 1.1, 2.3, 11.3, 11.4
"""

from sudoku_solver_evaluator.models.grid import Grid


def has_row_conflict(grid: Grid, row: int, col: int, value: int) -> bool:
    """Check if a value already exists in the same row, excluding the cell itself.

    Scans all cells in the given row. If any cell other than (row, col)
    already holds the specified value, there is a row conflict.

    Args:
        grid: The current Sudoku grid.
        row: Row index (0-8) of the cell being checked.
        col: Column index (0-8) of the cell being checked.
        value: The value (1-9) to check for conflicts.

    Returns:
        True if there IS a conflict (value already exists in the row),
        False otherwise.
    """
    # Iterate through all cells in the row
    for c in range(9):
        # Skip the cell itself to avoid false positives
        if c == col:
            continue
        cell = grid.get_cell(row, c)
        # A conflict exists if another cell in the row has the same value
        if cell.value == value:
            return True
    return False


def has_col_conflict(grid: Grid, row: int, col: int, value: int) -> bool:
    """Check if a value already exists in the same column, excluding the cell itself.

    Scans all cells in the given column. If any cell other than (row, col)
    already holds the specified value, there is a column conflict.

    Args:
        grid: The current Sudoku grid.
        row: Row index (0-8) of the cell being checked.
        col: Column index (0-8) of the cell being checked.
        value: The value (1-9) to check for conflicts.

    Returns:
        True if there IS a conflict (value already exists in the column),
        False otherwise.
    """
    # Iterate through all cells in the column
    for r in range(9):
        # Skip the cell itself to avoid false positives
        if r == row:
            continue
        cell = grid.get_cell(r, col)
        # A conflict exists if another cell in the column has the same value
        if cell.value == value:
            return True
    return False


def has_box_conflict(grid: Grid, row: int, col: int, value: int) -> bool:
    """Check if a value already exists in the same 3x3 box, excluding the cell itself.

    Determines which 3x3 box the cell belongs to, then scans all cells in
    that box. If any cell other than (row, col) already holds the specified
    value, there is a box conflict.

    The 3x3 boxes are defined by integer division of row and column indices
    by 3, giving the top-left corner of the box.

    Args:
        grid: The current Sudoku grid.
        row: Row index (0-8) of the cell being checked.
        col: Column index (0-8) of the cell being checked.
        value: The value (1-9) to check for conflicts.

    Returns:
        True if there IS a conflict (value already exists in the box),
        False otherwise.
    """
    # Calculate the top-left corner of the 3x3 box containing (row, col)
    box_start_row = (row // 3) * 3
    box_start_col = (col // 3) * 3

    # Iterate through all 9 cells in the 3x3 box
    for r in range(box_start_row, box_start_row + 3):
        for c in range(box_start_col, box_start_col + 3):
            # Skip the cell itself
            if r == row and c == col:
                continue
            cell = grid.get_cell(r, c)
            # A conflict exists if another cell in the box has the same value
            if cell.value == value:
                return True
    return False


def is_valid_assignment(grid: Grid, row: int, col: int, value: int) -> bool:
    """Check if assigning a value to a cell would violate any Sudoku constraint.

    An assignment is valid if the value does not already appear in the same
    row, column, or 3x3 box (excluding the cell itself). This is the primary
    function used by solvers to test candidate values before placing them.

    Args:
        grid: The current Sudoku grid.
        row: Row index (0-8) of the target cell.
        col: Column index (0-8) of the target cell.
        value: The value (1-9) to test for validity.

    Returns:
        True if the assignment is valid (no conflicts in row, column, or box),
        False if the assignment would violate any constraint.
    """
    # An assignment is valid only if it causes no conflict in any unit
    # (row, column, or box). We check all three constraints.
    if has_row_conflict(grid, row, col, value):
        return False
    if has_col_conflict(grid, row, col, value):
        return False
    if has_box_conflict(grid, row, col, value):
        return False
    return True


def get_conflicts(grid: Grid, row: int, col: int) -> list[tuple[int, int]]:
    """Get all cells that conflict with the value at the specified cell.

    A conflict occurs when another cell in the same row, column, or 3x3 box
    holds the same value as the cell at (row, col). If the cell has no value
    (is empty), returns an empty list.

    Args:
        grid: The current Sudoku grid.
        row: Row index (0-8) of the cell to check.
        col: Column index (0-8) of the cell to check.

    Returns:
        A list of (row, col) tuples identifying all cells that conflict
        with the specified cell. Returns an empty list if the cell is empty
        or has no conflicts.
    """
    cell = grid.get_cell(row, col)

    # If the cell has no value, there can be no conflicts
    if cell.value is None:
        return []

    value = cell.value
    conflicts: list[tuple[int, int]] = []

    # Use a set to avoid duplicate entries when a cell conflicts via
    # multiple units (e.g., same row AND same box)
    seen: set[tuple[int, int]] = set()

    # Check row conflicts: scan all other cells in the same row
    for c in range(9):
        if c == col:
            continue
        if grid.get_cell(row, c).value == value and (row, c) not in seen:
            conflicts.append((row, c))
            seen.add((row, c))

    # Check column conflicts: scan all other cells in the same column
    for r in range(9):
        if r == row:
            continue
        if grid.get_cell(r, col).value == value and (r, col) not in seen:
            conflicts.append((r, col))
            seen.add((r, col))

    # Check box conflicts: scan all other cells in the same 3x3 box
    box_start_row = (row // 3) * 3
    box_start_col = (col // 3) * 3
    for r in range(box_start_row, box_start_row + 3):
        for c in range(box_start_col, box_start_col + 3):
            if r == row and c == col:
                continue
            if grid.get_cell(r, c).value == value and (r, c) not in seen:
                conflicts.append((r, c))
                seen.add((r, c))

    return conflicts


def is_grid_valid(grid: Grid) -> bool:
    """Check if the entire grid has no constraint violations.

    Validates that no row, column, or 3x3 box contains duplicate non-zero
    values. Empty cells (value is None) are ignored. This function checks
    all 27 units (9 rows + 9 columns + 9 boxes) for the uniqueness constraint.

    Args:
        grid: The Sudoku grid to validate.

    Returns:
        True if the grid is valid (no duplicate non-zero values in any
        row, column, or box), False otherwise.
    """
    # Check all 9 rows for duplicate values
    for row in range(9):
        values = []
        for col in range(9):
            val = grid.get_cell(row, col).value
            if val is not None:
                values.append(val)
        # If there are duplicates, the set will be smaller than the list
        if len(values) != len(set(values)):
            return False

    # Check all 9 columns for duplicate values
    for col in range(9):
        values = []
        for row in range(9):
            val = grid.get_cell(row, col).value
            if val is not None:
                values.append(val)
        if len(values) != len(set(values)):
            return False

    # Check all 9 boxes (3x3 sub-grids) for duplicate values
    for box in range(9):
        # Calculate the top-left corner of each box
        box_start_row = (box // 3) * 3
        box_start_col = (box % 3) * 3
        values = []
        for r in range(box_start_row, box_start_row + 3):
            for c in range(box_start_col, box_start_col + 3):
                val = grid.get_cell(r, c).value
                if val is not None:
                    values.append(val)
        if len(values) != len(set(values)):
            return False

    return True
