from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.text import Text
from sudoku_solver_evaluator.models.grid import Grid
STYLE_FIXED = 'bold white'
STYLE_SOLVER_ASSIGNED = 'green'
STYLE_EMPTY = 'dim'
STYLE_HIGHLIGHT = 'bold yellow on dark_goldenrod'
STYLE_HIGHLIGHT_SWAP = 'bold magenta on purple4'
EMPTY_PLACEHOLDER = '.'

def render_grid(grid: Grid, highlight_cell: Optional[tuple[int, int]]=None, highlight_swap: Optional[tuple[int, int]]=None) -> Table:
    table = Table(title='Sudoku', show_header=False, show_lines=True, border_style='bright_blue', pad_edge=True, padding=(0, 1))
    for col_idx in range(9):
        table.add_column(justify='center', width=3, no_wrap=True)
    for row_idx in range(9):
        row_cells: list[Text] = []
        for col_idx in range(9):
            cell = grid.get_cell(row_idx, col_idx)
            text = _format_cell(cell.value, cell.is_fixed, row_idx, col_idx, highlight_cell, highlight_swap)
            row_cells.append(text)
        end_section = row_idx % 3 == 2 and row_idx < 8
        table.add_row(*row_cells, end_section=end_section)
    return table

def _format_cell(value: Optional[int], is_fixed: bool, row: int, col: int, highlight_cell: Optional[tuple[int, int]], highlight_swap: Optional[tuple[int, int]]) -> Text:
    is_active = highlight_cell is not None and (row, col) == highlight_cell
    is_swap = highlight_swap is not None and (row, col) == highlight_swap
    if value is None:
        display = EMPTY_PLACEHOLDER
    else:
        display = str(value)
    if is_active:
        style = STYLE_HIGHLIGHT
    elif is_swap:
        style = STYLE_HIGHLIGHT_SWAP
    elif value is None:
        style = STYLE_EMPTY
    elif is_fixed:
        style = STYLE_FIXED
    else:
        style = STYLE_SOLVER_ASSIGNED
    return Text(display, style=style)

def print_grid(grid: Grid, highlight_cell: Optional[tuple[int, int]]=None, highlight_swap: Optional[tuple[int, int]]=None, console: Optional[Console]=None) -> None:
    if console is None:
        console = Console()
    table = render_grid(grid, highlight_cell=highlight_cell, highlight_swap=highlight_swap)
    console.print(table)