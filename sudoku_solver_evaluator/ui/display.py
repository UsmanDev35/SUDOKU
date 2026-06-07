"""Grid display module with Rich-based formatting.

Provides functions to render a 9x9 Sudoku grid in the terminal using
the Rich library, with visual separators for rows, columns, and 3x3 boxes.
Pre-filled cells are distinguished from solver-assigned cells using
distinct colors and styles, and active cells can be highlighted during
step-by-step visualization.
"""

from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from sudoku_solver_evaluator.models.grid import Grid


# Style constants for cell rendering
STYLE_FIXED = "bold white"
STYLE_SOLVER_ASSIGNED = "green"
STYLE_EMPTY = "dim"
STYLE_HIGHLIGHT = "bold yellow on dark_goldenrod"
STYLE_HIGHLIGHT_SWAP = "bold magenta on purple4"

# Placeholder for empty cells
EMPTY_PLACEHOLDER = "."


def render_grid(
    grid: Grid,
    highlight_cell: Optional[tuple[int, int]] = None,
    highlight_swap: Optional[tuple[int, int]] = None,
) -> Table:
    """Render a Sudoku grid as a Rich Table with box separators and cell styling.

    Displays the 9x9 grid with:
    - Row, column, and 3x3 box separators using Rich Table borders
    - Pre-filled (fixed) cells in bold white
    - Solver-assigned cells in green
    - Empty cells as a dot placeholder in dim style
    - Active cell highlighted with yellow background (step-by-step mode)
    - Swap cell highlighted with magenta background (SA step-by-step mode)

    Args:
        grid: The Grid object to render.
        highlight_cell: Optional (row, col) tuple of the active cell to highlight.
        highlight_swap: Optional (row, col) tuple of the swap target cell to highlight.

    Returns:
        A Rich Table object ready for printing to the console.
    """
    table = Table(
        title="Sudoku",
        show_header=False,
        show_lines=True,
        border_style="bright_blue",
        pad_edge=True,
        padding=(0, 1),
    )

    # Add 9 columns with section separators at box boundaries
    for col_idx in range(9):
        table.add_column(justify="center", width=3, no_wrap=True)

    for row_idx in range(9):
        row_cells: list[Text] = []
        for col_idx in range(9):
            cell = grid.get_cell(row_idx, col_idx)
            text = _format_cell(
                cell.value,
                cell.is_fixed,
                row_idx,
                col_idx,
                highlight_cell,
                highlight_swap,
            )
            row_cells.append(text)

        # Add a section separator after every 3rd row (except the last)
        end_section = (row_idx % 3 == 2) and (row_idx < 8)
        table.add_row(*row_cells, end_section=end_section)

    return table


def _format_cell(
    value: Optional[int],
    is_fixed: bool,
    row: int,
    col: int,
    highlight_cell: Optional[tuple[int, int]],
    highlight_swap: Optional[tuple[int, int]],
) -> Text:
    """Format a single cell with appropriate styling.

    Args:
        value: The cell's value (1-9) or None if empty.
        is_fixed: Whether the cell is pre-filled.
        row: Row index of the cell.
        col: Column index of the cell.
        highlight_cell: The active cell position to highlight, or None.
        highlight_swap: The swap target cell position to highlight, or None.

    Returns:
        A Rich Text object with applied styling.
    """
    # Determine if this cell is highlighted
    is_active = highlight_cell is not None and (row, col) == highlight_cell
    is_swap = highlight_swap is not None and (row, col) == highlight_swap

    # Determine display text
    if value is None:
        display = EMPTY_PLACEHOLDER
    else:
        display = str(value)

    # Determine style based on priority: highlight > swap > fixed/assigned/empty
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


def print_grid(
    grid: Grid,
    highlight_cell: Optional[tuple[int, int]] = None,
    highlight_swap: Optional[tuple[int, int]] = None,
    console: Optional[Console] = None,
) -> None:
    """Print the rendered grid to the console.

    Convenience function that renders and immediately prints the grid.

    Args:
        grid: The Grid object to display.
        highlight_cell: Optional (row, col) tuple of the active cell to highlight.
        highlight_swap: Optional (row, col) tuple of the swap target cell to highlight.
        console: Optional Rich Console instance. Creates a new one if not provided.
    """
    if console is None:
        console = Console()

    table = render_grid(grid, highlight_cell=highlight_cell, highlight_swap=highlight_swap)
    console.print(table)
