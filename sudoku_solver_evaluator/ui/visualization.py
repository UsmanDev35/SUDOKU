from __future__ import annotations
import sys
import threading
import time
from typing import Generator, Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from sudoku_solver_evaluator.models.enums import StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
DEFAULT_DELAY_MS = 500
MIN_DELAY_MS = 100
MAX_DELAY_MS = 2000

def clamp_delay(delay_ms: int) -> int:
    return max(MIN_DELAY_MS, min(MAX_DELAY_MS, delay_ms))

class VisualizationController:

    def __init__(self, grid: Grid, delay_ms: int=DEFAULT_DELAY_MS) -> None:
        self.delay_ms: int = clamp_delay(delay_ms)
        self.grid: Grid = grid.copy()
        self.states_explored: int = 0
        self.backtracks: int = 0
        self.is_paused: bool = False
        self.is_skipping: bool = False
        self.is_running: bool = False
        self._highlight_cells: list[tuple[int, int]] = []
        self._is_backtrack: bool = False
        self._is_swap: bool = False
        self._step_label: str = ''
        self._console = Console()
        self._input_thread: Optional[threading.Thread] = None

    def set_delay(self, delay_ms: int) -> None:
        self.delay_ms = clamp_delay(delay_ms)

    def run(self, step_generator: Generator[StepEvent, None, SolveResult]) -> SolveResult:
        self.is_running = True
        self.is_paused = False
        self.is_skipping = False
        self._start_input_listener()
        result: Optional[SolveResult] = None
        try:
            with Live(self._render_display(), console=self._console, refresh_per_second=10, transient=False) as live:
                try:
                    while True:
                        while self.is_paused and (not self.is_skipping):
                            live.update(self._render_display())
                            time.sleep(0.1)
                        try:
                            step_event = next(step_generator)
                        except StopIteration as e:
                            result = e.value
                            break
                        self._process_step(step_event)
                        live.update(self._render_display())
                        if not self.is_skipping:
                            time.sleep(self.delay_ms / 1000.0)
                except StopIteration as e:
                    result = e.value
                self._highlight_cells = []
                self._is_backtrack = False
                self._is_swap = False
                self._step_label = 'COMPLETE'
                live.update(self._render_display())
        finally:
            self.is_running = False
        return result

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def skip_to_end(self) -> None:
        self.is_skipping = True
        self.is_paused = False

    def _process_step(self, event: StepEvent) -> None:
        self.states_explored = event.states_explored
        self.backtracks = event.backtracks
        self._highlight_cells = []
        self._is_backtrack = False
        self._is_swap = False
        self._step_label = ''
        if event.step_type == StepType.ASSIGN:
            self.grid.set_value(event.row, event.col, event.value)
            self._highlight_cells = [(event.row, event.col)]
            self._step_label = f'ASSIGN ({event.row},{event.col}) = {event.value}'
        elif event.step_type == StepType.BACKTRACK:
            self.grid.clear_value(event.row, event.col)
            self._highlight_cells = [(event.row, event.col)]
            self._is_backtrack = True
            self._step_label = 'BACKTRACK'
        elif event.step_type == StepType.SWAP:
            cell1_val = self.grid.get_cell(event.row, event.col).value
            cell2_val = None
            if event.swap_row is not None and event.swap_col is not None:
                cell2_val = self.grid.get_cell(event.swap_row, event.swap_col).value
                self.grid.set_value(event.row, event.col, cell2_val if cell2_val else 0)
                self.grid.set_value(event.swap_row, event.swap_col, cell1_val if cell1_val else 0)
                self._highlight_cells = [(event.row, event.col), (event.swap_row, event.swap_col)]
            else:
                self._highlight_cells = [(event.row, event.col)]
            self._is_swap = True
            self._step_label = 'SWAP'
        elif event.step_type == StepType.PROPAGATE:
            if event.value is not None:
                self.grid.set_value(event.row, event.col, event.value)
            self._highlight_cells = [(event.row, event.col)]
            self._step_label = f'PROPAGATE ({event.row},{event.col})'

    def _render_display(self) -> Panel:
        grid_table = self._render_grid()
        status_parts = []
        if self._step_label:
            if self._is_backtrack:
                status_parts.append(Text(f'  [{self._step_label}]', style='bold red'))
            elif self._is_swap:
                status_parts.append(Text(f'  [{self._step_label}]', style='bold magenta'))
            else:
                status_parts.append(Text(f'  [{self._step_label}]', style='bold green'))
        metrics_text = Text(f'\n  States explored: {self.states_explored}  |  Backtracks: {self.backtracks}', style='cyan')
        if self.is_paused:
            controls_text = Text('\n  [PAUSED] Controls: r=resume, s=skip to end', style='yellow')
        else:
            controls_text = Text('\n  Controls: p=pause, r=resume, s=skip to end', style='dim')
        display = Text()
        display.append_text(Text('\n'))
        display.append_text(status_parts[0] if status_parts else Text(''))
        display.append_text(metrics_text)
        display.append_text(controls_text)
        display.append_text(Text('\n'))
        panel_content = Text()
        panel_content.append('\n')
        grid_lines = self._render_grid_text()
        panel_content.append_text(grid_lines)
        panel_content.append('\n')
        panel_content.append_text(display)
        title = 'Step-by-Step Visualization'
        if self.is_paused:
            title += ' [PAUSED]'
        elif self.is_skipping:
            title += ' [SKIPPING]'
        return Panel(panel_content, title=title, border_style='blue')

    def _render_grid_text(self) -> Text:
        text = Text()
        text.append('     1  2  3   4  5  6   7  8  9\n', style='dim')
        text.append('   +' + '---' * 3 + '+' + '---' * 3 + '+' + '---' * 3 + '+\n', style='dim')
        for row in range(9):
            if row > 0 and row % 3 == 0:
                text.append('   +' + '---' * 3 + '+' + '---' * 3 + '+' + '---' * 3 + '+\n', style='dim')
            text.append(f' {row + 1} |', style='dim')
            for col in range(9):
                if col > 0 and col % 3 == 0:
                    text.append('|', style='dim')
                cell = self.grid.get_cell(row, col)
                is_highlighted = (row, col) in self._highlight_cells
                if cell.value is not None:
                    val_str = f' {cell.value} '
                else:
                    val_str = ' . '
                if is_highlighted:
                    if self._is_backtrack:
                        style = 'bold white on red'
                    elif self._is_swap:
                        style = 'bold white on magenta'
                    else:
                        style = 'bold white on green'
                elif cell.is_fixed:
                    style = 'bold white'
                else:
                    style = 'cyan'
                text.append(val_str, style=style)
            text.append('|', style='dim')
            text.append('\n')
        text.append('   +' + '---' * 3 + '+' + '---' * 3 + '+' + '---' * 3 + '+\n', style='dim')
        return text

    def _render_grid(self) -> Table:
        table = Table(show_header=False, show_lines=True, padding=0)
        for _ in range(9):
            table.add_column(width=3, justify='center')
        for row in range(9):
            row_cells = []
            for col in range(9):
                cell = self.grid.get_cell(row, col)
                if cell.value is not None:
                    row_cells.append(str(cell.value))
                else:
                    row_cells.append('.')
            table.add_row(*row_cells)
        return table

    def _start_input_listener(self) -> None:
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True, name='viz-input-listener')
        self._input_thread.start()

    def _input_loop(self) -> None:
        try:
            if sys.platform == 'win32':
                self._input_loop_windows()
            else:
                self._input_loop_unix()
        except Exception:
            pass

    def _input_loop_windows(self) -> None:
        try:
            import msvcrt
            while self.is_running:
                if msvcrt.kbhit():
                    ch = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                    self._handle_key(ch)
                else:
                    time.sleep(0.05)
        except ImportError:
            pass

    def _input_loop_unix(self) -> None:
        try:
            import select
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while self.is_running:
                    if select.select([sys.stdin], [], [], 0.05)[0]:
                        ch = sys.stdin.read(1).lower()
                        self._handle_key(ch)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, OSError):
            pass

    def _handle_key(self, key: str) -> None:
        if key == 'p':
            self.pause()
        elif key == 'r':
            self.resume()
        elif key == 's':
            self.skip_to_end()

def run_visualization(grid: Grid, step_generator: Generator[StepEvent, None, SolveResult], delay_ms: int=DEFAULT_DELAY_MS) -> SolveResult:
    controller = VisualizationController(grid=grid, delay_ms=delay_ms)
    return controller.run(step_generator)