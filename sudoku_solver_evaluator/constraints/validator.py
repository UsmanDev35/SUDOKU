from sudoku_solver_evaluator.models.grid import Grid

def has_row_conflict(grid: Grid, row: int, col: int, value: int) -> bool:
    for c in range(9):
        if c == col:
            continue
        cell = grid.get_cell(row, c)
        if cell.value == value:
            return True
    return False

def has_col_conflict(grid: Grid, row: int, col: int, value: int) -> bool:
    for r in range(9):
        if r == row:
            continue
        cell = grid.get_cell(r, col)
        if cell.value == value:
            return True
    return False

def has_box_conflict(grid: Grid, row: int, col: int, value: int) -> bool:
    box_start_row = row // 3 * 3
    box_start_col = col // 3 * 3
    for r in range(box_start_row, box_start_row + 3):
        for c in range(box_start_col, box_start_col + 3):
            if r == row and c == col:
                continue
            cell = grid.get_cell(r, c)
            if cell.value == value:
                return True
    return False

def is_valid_assignment(grid: Grid, row: int, col: int, value: int) -> bool:
    if has_row_conflict(grid, row, col, value):
        return False
    if has_col_conflict(grid, row, col, value):
        return False
    if has_box_conflict(grid, row, col, value):
        return False
    return True

def get_conflicts(grid: Grid, row: int, col: int) -> list[tuple[int, int]]:
    cell = grid.get_cell(row, col)
    if cell.value is None:
        return []
    value = cell.value
    conflicts: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for c in range(9):
        if c == col:
            continue
        if grid.get_cell(row, c).value == value and (row, c) not in seen:
            conflicts.append((row, c))
            seen.add((row, c))
    for r in range(9):
        if r == row:
            continue
        if grid.get_cell(r, col).value == value and (r, col) not in seen:
            conflicts.append((r, col))
            seen.add((r, col))
    box_start_row = row // 3 * 3
    box_start_col = col // 3 * 3
    for r in range(box_start_row, box_start_row + 3):
        for c in range(box_start_col, box_start_col + 3):
            if r == row and c == col:
                continue
            if grid.get_cell(r, c).value == value and (r, c) not in seen:
                conflicts.append((r, c))
                seen.add((r, c))
    return conflicts

def is_grid_valid(grid: Grid) -> bool:
    for row in range(9):
        values = []
        for col in range(9):
            val = grid.get_cell(row, col).value
            if val is not None:
                values.append(val)
        if len(values) != len(set(values)):
            return False
    for col in range(9):
        values = []
        for row in range(9):
            val = grid.get_cell(row, col).value
            if val is not None:
                values.append(val)
        if len(values) != len(set(values)):
            return False
    for box in range(9):
        box_start_row = box // 3 * 3
        box_start_col = box % 3 * 3
        values = []
        for r in range(box_start_row, box_start_row + 3):
            for c in range(box_start_col, box_start_col + 3):
                val = grid.get_cell(r, c).value
                if val is not None:
                    values.append(val)
        if len(values) != len(set(values)):
            return False
    return True