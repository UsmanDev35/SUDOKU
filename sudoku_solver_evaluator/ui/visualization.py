"""Step-by-step visualization controller for Sudoku solving.

Provides real-time display of solver step events using Rich's Live display.
Supports configurable delay, pause/resume controls, and highlights active
cells, backtrack events, and swap operations.

Requirements: 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

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


# Default delay between visualization steps in milliseconds
DEFAULT_DELAY_MS = 500

# Valid delay range in milliseconds
MIN_DELAY_MS = 100
MAX_DELAY_MS = 2000


def clamp_delay(delay_ms: int) -> int:
    """Clamp the delay value to the valid range [100, 2000] ms.

    Args:
        delay_ms: The requested delay in milliseconds.

    Returns:
        The delay clamped to the valid range.
    """
    return max(MIN_DELAY_MS, min(MAX_DELAY_MS, delay_ms))


class VisualizationController:
    """Controls step-by-step playback of solver events.

    Accepts a StepEvent generator from a solver's solve_stepwise method
    and displays each state transition in real-time using Rich Live display.

    Features:
        - Configurable delay between steps (100-2000ms)
        - BACKTRACK label display on backtrack events
        - Swap cell highlighting for SA solver
        - Running metrics display (states explored, backtracks)
        - Keyboard controls: pause (p), resume (r), skip to end (s)

    Attributes:
        delay_ms: Delay between steps in milliseconds (clamped to 100-2000).
        grid: The current grid state being visualized.
        states_explored: Running count of states explored.
        backtracks: Running count of backtracks.
        is_paused: Whether visualization is currently paused.
        is_skipping: Whether visualization is skipping to completion.
        is_running: Whether the visualization loop is active.
    """

    def __init__(self, grid: Grid, delay_ms: int = DEFAULT_DELAY_MS) -> None:
        """Initialize the visualization controller.

        Args:
            grid: The initial puzzle grid to visualize.
            delay_ms: Delay between steps in milliseconds. Clamped to [100, 2000].
        """
        self.delay_ms: int = clamp_delay(delay_ms)
        self.grid: Grid = grid.copy()
        self.states_explored: int = 0
        self.backtracks: int = 0
        self.is_paused: bool = False
        self.is_skipping: bool = False
        self.is_running: bool = False

        # Highlight state for current step
        self._highlight_cells: list[tuple[int, int]] = []
        self._is_backtrack: bool = False
        self._is_swap: bool = False
        self._step_label: str = ""

        self._console = Console()
        self._input_thread: Optional[threading.Thread] = None

    def set_delay(self, delay_ms: int) -> None:
        """Set the delay between steps.

        Args:
            delay_ms: New delay in milliseconds. Clamped to [100, 2000].
        """
        self.delay_ms = clamp_delay(delay_ms)

    def run(
        self, step_generator: Generator[StepEvent, None, SolveResult]
    ) -> SolveResult:
        """Run the step-by-step visualization.

        Consumes StepEvent objects from the generator, updates the grid
        display after each step, and returns the final SolveResult.

        Supports keyboard controls:
            - p: Pause visualization
            - r: Resume visualization
            - s: Skip to completion (process all remaining steps instantly)

        Args:
            step_generator: A generator yielding StepEvent objects,
                returning a SolveResult on completion.

        Returns:
            The SolveResult from the solver upon completion.
        """
        self.is_running = True
        self.is_paused = False
        self.is_skipping = False

        # Start keyboard input listener thread
        self._start_input_listener()

        result: Optional[SolveResult] = None

        try:
            with Live(
                self._render_display(),
                console=self._console,
                refresh_per_second=10,
                transient=False,
            ) as live:
                try:
                    while True:
                        # Wait while paused
                        while self.is_paused and not self.is_skipping:
                            live.update(self._render_display())
                            time.sleep(0.1)

                        # Get next step event from generator
                        try:
                            step_event = next(step_generator)
                        except StopIteration as e:
                            # Generator returned the final SolveResult
                            result = e.value
                            break

                        # Process the step event
                        self._process_step(step_event)

                        # Update the live display
                        live.update(self._render_display())

                        # Apply delay between steps (unless skipping)
                        if not self.is_skipping:
                            time.sleep(self.delay_ms / 1000.0)

                except StopIteration as e:
                    result = e.value

                # Final display update with cleared highlights
                self._highlight_cells = []
                self._is_backtrack = False
                self._is_swap = False
                self._step_label = "COMPLETE"
                live.update(self._render_display())

        finally:
            self.is_running = False

        return result

    def pause(self) -> None:
        """Pause the visualization playback."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume the visualization playback."""
        self.is_paused = False

    def skip_to_end(self) -> None:
        """Skip to completion, processing all remaining steps instantly."""
        self.is_skipping = True
        self.is_paused = False

    def _process_step(self, event: StepEvent) -> None:
        """Process a single step event and update internal state.

        Updates the grid, metrics counters, and highlight state based
        on the step event type.

        Args:
            event: The StepEvent to process.
        """
        # Update running metrics
        self.states_explored = event.states_explored
        self.backtracks = event.backtracks

        # Clear previous highlights
        self._highlight_cells = []
        self._is_backtrack = False
        self._is_swap = False
        self._step_label = ""

        if event.step_type == StepType.ASSIGN:
            # Assign value to cell
            self.grid.set_value(event.row, event.col, event.value)
            self._highlight_cells = [(event.row, event.col)]
            self._step_label = f"ASSIGN ({event.row},{event.col}) = {event.value}"

        elif event.step_type == StepType.BACKTRACK:
            # Clear the cell (revert assignment)
            self.grid.clear_value(event.row, event.col)
            self._highlight_cells = [(event.row, event.col)]
            self._is_backtrack = True
            self._step_label = "BACKTRACK"

        elif event.step_type == StepType.SWAP:
            # Swap two cells (SA solver)
            # Apply the swap by reading current values and swapping them
            cell1_val = self.grid.get_cell(event.row, event.col).value
            cell2_val = None
            if event.swap_row is not None and event.swap_col is not None:
                cell2_val = self.grid.get_cell(event.swap_row, event.swap_col).value
                self.grid.set_value(event.row, event.col, cell2_val if cell2_val else 0)
                self.grid.set_value(event.swap_row, event.swap_col, cell1_val if cell1_val else 0)
                self._highlight_cells = [
                    (event.row, event.col),
                    (event.swap_row, event.swap_col),
                ]
            else:
                self._highlight_cells = [(event.row, event.col)]
            self._is_swap = True
            self._step_label = "SWAP"

        elif event.step_type == StepType.PROPAGATE:
            # Domain propagation - just highlight the cell
            if event.value is not None:
                self.grid.set_value(event.row, event.col, event.value)
            self._highlight_cells = [(event.row, event.col)]
            self._step_label = f"PROPAGATE ({event.row},{event.col})"

    def _render_display(self) -> Panel:
        """Render the current visualization state as a Rich Panel.

        Creates a formatted display including:
        - The 9x9 grid with highlighting
        - Step label (BACKTRACK, SWAP, etc.)
        - Running metrics
        - Control instructions

        Returns:
            A Rich Panel containing the full visualization.
        """
        # Build the grid table
        grid_table = self._render_grid()

        # Build metrics and status text
        status_parts = []

        # Step label
        if self._step_label:
            if self._is_backtrack:
                status_parts.append(Text(f"  [{self._step_label}]", style="bold red"))
            elif self._is_swap:
                status_parts.append(Text(f"  [{self._step_label}]", style="bold magenta"))
            else:
                status_parts.append(Text(f"  [{self._step_label}]", style="bold green"))

        # Metrics line
        metrics_text = Text(
            f"\n  States explored: {self.states_explored}  |  "
            f"Backtracks: {self.backtracks}",
            style="cyan",
        )

        # Controls line
        if self.is_paused:
            controls_text = Text(
                "\n  [PAUSED] Controls: r=resume, s=skip to end", style="yellow"
            )
        else:
            controls_text = Text(
                "\n  Controls: p=pause, r=resume, s=skip to end", style="dim"
            )

        # Compose the full display
        display = Text()
        display.append_text(Text("\n"))
        display.append_text(status_parts[0] if status_parts else Text(""))
        display.append_text(metrics_text)
        display.append_text(controls_text)
        display.append_text(Text("\n"))

        panel_content = Text()
        panel_content.append("\n")
        # We'll render grid as text lines
        grid_lines = self._render_grid_text()
        panel_content.append_text(grid_lines)
        panel_content.append("\n")
        panel_content.append_text(display)

        title = "Step-by-Step Visualization"
        if self.is_paused:
            title += " [PAUSED]"
        elif self.is_skipping:
            title += " [SKIPPING]"

        return Panel(panel_content, title=title, border_style="blue")

    def _render_grid_text(self) -> Text:
        """Render the 9x9 grid as formatted Rich Text with highlighting.

        Renders the grid with:
        - Row/column separators for 3x3 boxes
        - Distinct colors for fixed vs solver-assigned cells
        - Highlighted cells (green for assign, red for backtrack, magenta for swap)

        Returns:
            Rich Text object containing the formatted grid.
        """
        text = Text()

        # Column header
        text.append("     1  2  3   4  5  6   7  8  9\n", style="dim")
        text.append("   +" + "---" * 3 + "+" + "---" * 3 + "+" + "---" * 3 + "+\n", style="dim")

        for row in range(9):
            # Row separator for box boundaries
            if row > 0 and row % 3 == 0:
                text.append(
                    "   +" + "---" * 3 + "+" + "---" * 3 + "+" + "---" * 3 + "+\n",
                    style="dim",
                )

            # Row label
            text.append(f" {row + 1} |", style="dim")

            for col in range(9):
                # Box separator
                if col > 0 and col % 3 == 0:
                    text.append("|", style="dim")

                cell = self.grid.get_cell(row, col)
                is_highlighted = (row, col) in self._highlight_cells

                # Determine cell display value
                if cell.value is not None:
                    val_str = f" {cell.value} "
                else:
                    val_str = " . "

                # Determine style based on state
                if is_highlighted:
                    if self._is_backtrack:
                        style = "bold white on red"
                    elif self._is_swap:
                        style = "bold white on magenta"
                    else:
                        style = "bold white on green"
                elif cell.is_fixed:
                    style = "bold white"
                else:
                    style = "cyan"

                text.append(val_str, style=style)

            text.append("|", style="dim")
            text.append("\n")

        # Bottom border
        text.append("   +" + "---" * 3 + "+" + "---" * 3 + "+" + "---" * 3 + "+\n", style="dim")

        return text

    def _render_grid(self) -> Table:
        """Render the grid as a Rich Table (alternative representation).

        Returns:
            Rich Table with the grid contents.
        """
        table = Table(show_header=False, show_lines=True, padding=0)
        for _ in range(9):
            table.add_column(width=3, justify="center")

        for row in range(9):
            row_cells = []
            for col in range(9):
                cell = self.grid.get_cell(row, col)
                if cell.value is not None:
                    row_cells.append(str(cell.value))
                else:
                    row_cells.append(".")
            table.add_row(*row_cells)

        return table

    def _start_input_listener(self) -> None:
        """Start a background thread listening for keyboard input.

        Listens for control keys:
            - p: Pause
            - r: Resume
            - s: Skip to end

        The thread runs as a daemon and terminates when the main
        visualization loop ends.
        """
        self._input_thread = threading.Thread(
            target=self._input_loop, daemon=True, name="viz-input-listener"
        )
        self._input_thread.start()

    def _input_loop(self) -> None:
        """Background loop reading keyboard input for controls.

        Reads single characters from stdin and maps them to control actions.
        Runs until is_running becomes False.
        """
        try:
            # Use platform-specific non-blocking input if available
            if sys.platform == "win32":
                self._input_loop_windows()
            else:
                self._input_loop_unix()
        except Exception:
            # Silently ignore input errors - visualization continues without controls
            pass

    def _input_loop_windows(self) -> None:
        """Windows-specific keyboard input handling using msvcrt."""
        try:
            import msvcrt

            while self.is_running:
                if msvcrt.kbhit():
                    ch = msvcrt.getch().decode("utf-8", errors="ignore").lower()
                    self._handle_key(ch)
                else:
                    time.sleep(0.05)
        except ImportError:
            # msvcrt not available, fall back to no input handling
            pass

    def _input_loop_unix(self) -> None:
        """Unix-specific keyboard input handling using termios."""
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
            # Terminal not available, fall back to no input handling
            pass

    def _handle_key(self, key: str) -> None:
        """Handle a keyboard control key press.

        Args:
            key: The single character key pressed.
        """
        if key == "p":
            self.pause()
        elif key == "r":
            self.resume()
        elif key == "s":
            self.skip_to_end()


def run_visualization(
    grid: Grid,
    step_generator: Generator[StepEvent, None, SolveResult],
    delay_ms: int = DEFAULT_DELAY_MS,
) -> SolveResult:
    """Convenience function to run step-by-step visualization.

    Creates a VisualizationController and runs the visualization loop
    with the given step generator.

    Args:
        grid: The initial puzzle grid.
        step_generator: Generator yielding StepEvent objects from a solver.
        delay_ms: Delay between steps in milliseconds. Clamped to [100, 2000].

    Returns:
        The SolveResult from the solver upon completion.
    """
    controller = VisualizationController(grid=grid, delay_ms=delay_ms)
    return controller.run(step_generator)
