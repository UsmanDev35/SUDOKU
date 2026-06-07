from dataclasses import dataclass, field
from typing import Optional
import copy

@dataclass
class Cell:
    row: int
    col: int
    value: Optional[int] = None
    is_fixed: bool = False
    domain: set[int] = field(default_factory=lambda: set(range(1, 10)))

    @property
    def box(self) -> int:
        return self.row // 3 * 3 + self.col // 3

@dataclass
class Grid:
    cells: list[list[Cell]]

    def get_cell(self, row: int, col: int) -> Cell:
        return self.cells[row][col]

    def set_value(self, row: int, col: int, value: int) -> None:
        self.cells[row][col].value = value

    def clear_value(self, row: int, col: int) -> None:
        self.cells[row][col].value = None

    def get_row(self, row: int) -> list[Cell]:
        return self.cells[row]

    def get_col(self, col: int) -> list[Cell]:
        return [self.cells[row][col] for row in range(9)]

    def get_box(self, box_index: int) -> list[Cell]:
        start_row = box_index // 3 * 3
        start_col = box_index % 3 * 3
        cells = []
        for r in range(start_row, start_row + 3):
            for c in range(start_col, start_col + 3):
                cells.append(self.cells[r][c])
        return cells

    def get_peers(self, row: int, col: int) -> list[Cell]:
        peers: set[tuple[int, int]] = set()
        for c in range(9):
            if c != col:
                peers.add((row, c))
        for r in range(9):
            if r != row:
                peers.add((r, col))
        box_start_row = row // 3 * 3
        box_start_col = col // 3 * 3
        for r in range(box_start_row, box_start_row + 3):
            for c in range(box_start_col, box_start_col + 3):
                if (r, c) != (row, col):
                    peers.add((r, c))
        return [self.cells[r][c] for r, c in peers]

    def get_empty_cells(self) -> list[Cell]:
        empty = []
        for row in self.cells:
            for cell in row:
                if cell.value is None:
                    empty.append(cell)
        return empty

    def is_complete(self) -> bool:
        for row in self.cells:
            for cell in row:
                if cell.value is None:
                    return False
        return True

    def is_valid(self) -> bool:
        for row in range(9):
            if not self._is_unit_valid(self.get_row(row)):
                return False
        for col in range(9):
            if not self._is_unit_valid(self.get_col(col)):
                return False
        for box in range(9):
            if not self._is_unit_valid(self.get_box(box)):
                return False
        return True

    def _is_unit_valid(self, cells: list[Cell]) -> bool:
        values = [cell.value for cell in cells if cell.value is not None]
        return len(values) == len(set(values))

    def copy(self) -> 'Grid':
        new_cells = []
        for row in self.cells:
            new_row = []
            for cell in row:
                new_cell = Cell(row=cell.row, col=cell.col, value=cell.value, is_fixed=cell.is_fixed, domain=set(cell.domain))
                new_row.append(new_cell)
            new_cells.append(new_row)
        return Grid(cells=new_cells)

    def count_filled(self) -> int:
        count = 0
        for row in self.cells:
            for cell in row:
                if cell.value is not None:
                    count += 1
        return count

    @classmethod
    def from_2d_list(cls, values: list[list[int]]) -> 'Grid':
        cells = []
        for row in range(9):
            cell_row = []
            for col in range(9):
                val = values[row][col]
                if val == 0:
                    cell = Cell(row=row, col=col, value=None, is_fixed=False)
                else:
                    cell = Cell(row=row, col=col, value=val, is_fixed=True, domain={val})
                cell_row.append(cell)
            cells.append(cell_row)
        return cls(cells=cells)

    def to_2d_list(self) -> list[list[int]]:
        result = []
        for row in self.cells:
            result.append([cell.value if cell.value is not None else 0 for cell in row])
        return result