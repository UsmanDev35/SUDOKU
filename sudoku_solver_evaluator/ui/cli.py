"""Main CLI menu and navigation for the Sudoku Solver Evaluator.

Provides an interactive numbered menu system using Rich Console for output.
Handles puzzle generation, solver selection, step-by-step visualization,
dashboard display, adversarial mode, and CSV export.

Requirements: 8.1, 8.2, 8.6, 8.7, 8.8, 8.9
"""

from __future__ import annotations

import uuid
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.ui.dashboard import (
    render_aggregate_table,
    render_comparison_table,
    render_full_dashboard,
    render_performance_chart,
)
from sudoku_solver_evaluator.ui.display import print_grid
from sudoku_solver_evaluator.ui.visualization import VisualizationController


# Human-friendly solver names
_SOLVER_NAMES: dict[SolverType, str] = {
    SolverType.BACKTRACKING: "Backtracking Search",
    SolverType.INFORMED: "Informed (AC-3 + MRV + Degree)",
    SolverType.LOCAL_SEARCH: "Simulated Annealing",
    SolverType.FORWARD_CHECKING: "Forward Checking",
}

# Difficulty display names
_DIFFICULTY_NAMES: dict[DifficultyLevel, str] = {
    DifficultyLevel.EASY: "Easy (36-45 clues)",
    DifficultyLevel.MEDIUM: "Medium (27-35 clues)",
    DifficultyLevel.HARD: "Hard (22-26 clues)",
    DifficultyLevel.EXPERT: "Expert (17-21 clues)",
}


class CLI:
    """Main CLI controller for the Sudoku Solver Evaluator.

    Manages the main menu loop, user input handling, and navigation
    between all system features. Uses Rich Console for formatted output.

    Attributes:
        generator: PuzzleGenerator instance for creating puzzles.
        solver_manager: SolverManager instance with all registered solvers.
        evaluator: PerformanceEvaluator for recording and querying results.
        console: Rich Console for formatted output.
        current_puzzle: The most recently generated puzzle grid, or None.
        current_difficulty: Difficulty level of the current puzzle.
        current_puzzle_id: Unique ID of the current puzzle.
    """

    def __init__(
        self,
        generator: PuzzleGenerator,
        solver_manager: SolverManager,
        evaluator: PerformanceEvaluator,
        console: Optional[Console] = None,
    ) -> None:
        """Initialize the CLI with all required components.

        Args:
            generator: PuzzleGenerator instance.
            solver_manager: SolverManager with registered solvers.
            evaluator: PerformanceEvaluator for metrics tracking.
            console: Optional Rich Console instance; creates one if not provided.
        """
        self.generator = generator
        self.solver_manager = solver_manager
        self.evaluator = evaluator
        self.console = console or Console()
        self.current_puzzle: Optional[Grid] = None
        self.current_difficulty: Optional[DifficultyLevel] = None
        self.current_puzzle_id: Optional[str] = None

    def run(self) -> None:
        """Start the main menu loop.

        Displays the main menu and processes user selections until
        the user chooses to exit. Invalid input is handled gracefully
        with error messages and re-prompting.
        """
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]AI-Powered Multi-Level Sudoku Solver and Evaluator[/bold cyan]",
                border_style="bright_blue",
            )
        )

        while True:
            self._print_main_menu()
            choice = self._get_input("Select an option")

            if choice == "1":
                self._generate_puzzle()
            elif choice == "2":
                self._choose_solver()
            elif choice == "3":
                self._step_by_step_mode()
            elif choice == "4":
                self._view_dashboard()
            elif choice == "5":
                self._adversarial_mode()
            elif choice == "6":
                self._export_csv()
            elif choice == "7":
                self.console.print("\n[bold green]Goodbye![/bold green]\n")
                break
            else:
                self._show_invalid_input("1-7")

    def _print_main_menu(self) -> None:
        """Display the main menu options."""
        self.console.print()
        self.console.rule("[bold cyan]Main Menu[/bold cyan]")
        self.console.print()
        self.console.print("  [bold]1.[/bold] Generate Puzzle")
        self.console.print("  [bold]2.[/bold] Solve Puzzle")
        self.console.print("  [bold]3.[/bold] Step-by-Step Mode")
        self.console.print("  [bold]4.[/bold] View Dashboard")
        self.console.print("  [bold]5.[/bold] Adversarial Mode")
        self.console.print("  [bold]6.[/bold] Export Results to CSV")
        self.console.print("  [bold]7.[/bold] Exit")
        self.console.print()

    def _generate_puzzle(self) -> None:
        """Handle puzzle generation: prompt for difficulty, generate, and display."""
        self.console.print()
        self.console.rule("[bold]Generate Puzzle[/bold]")
        self.console.print()
        self.console.print("  Select difficulty level:")
        self.console.print()

        difficulties = list(DifficultyLevel)
        for i, diff in enumerate(difficulties, 1):
            self.console.print(f"  [bold]{i}.[/bold] {_DIFFICULTY_NAMES[diff]}")
        self.console.print()

        choice = self._get_input("Select difficulty (1-4)")

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(difficulties):
                self._show_invalid_input("1-4")
                return
        except ValueError:
            self._show_invalid_input("1-4")
            return

        difficulty = difficulties[idx]

        self.console.print(f"\n  Generating [bold]{difficulty.value}[/bold] puzzle...")
        try:
            puzzle = self.generator.generate(difficulty)
        except TimeoutError:
            self.console.print(
                "\n  [bold red]Error:[/bold red] Puzzle generation timed out. "
                "Please try again."
            )
            return

        # Store the generated puzzle
        self.current_puzzle = puzzle
        self.current_difficulty = difficulty
        self.current_puzzle_id = str(uuid.uuid4())[:8]

        self.console.print(
            f"\n  Puzzle generated! ID: [bold]{self.current_puzzle_id}[/bold]  "
            f"Filled cells: [bold]{puzzle.count_filled()}[/bold]"
        )
        self.console.print()
        print_grid(puzzle, console=self.console)

    def _choose_solver(self) -> None:
        """Handle solver selection: prompt for algorithm, solve, and display results."""
        if self.current_puzzle is None:
            self.console.print(
                "\n  [bold yellow]No puzzle generated yet.[/bold yellow] "
                "Please generate a puzzle first (option 1).\n"
            )
            return

        self.console.print()
        self.console.rule("[bold]Solve Puzzle[/bold]")
        self.console.print()
        self.console.print("  Select solver algorithm:")
        self.console.print()

        solvers = list(SolverType)
        for i, solver_type in enumerate(solvers, 1):
            self.console.print(f"  [bold]{i}.[/bold] {_SOLVER_NAMES[solver_type]}")
        self.console.print(f"  [bold]{len(solvers) + 1}.[/bold] Run All Solvers")
        self.console.print()

        choice = self._get_input(f"Select solver (1-{len(solvers) + 1})")

        try:
            idx = int(choice) - 1
            if idx < 0 or idx > len(solvers):
                self._show_invalid_input(f"1-{len(solvers) + 1}")
                return
        except ValueError:
            self._show_invalid_input(f"1-{len(solvers) + 1}")
            return

        if idx == len(solvers):
            # Run all solvers
            self._solve_all()
        else:
            # Run single solver
            solver_type = solvers[idx]
            self._solve_single(solver_type)

    def _solve_single(self, solver_type: SolverType) -> None:
        """Solve the current puzzle with a single solver and display results.

        Args:
            solver_type: The solver algorithm to use.
        """
        self.console.print(
            f"\n  Solving with [bold]{_SOLVER_NAMES[solver_type]}[/bold]..."
        )

        result = self.solver_manager.solve(self.current_puzzle, solver_type)

        # Record in evaluator
        self.evaluator.record(result, self.current_puzzle_id, self.current_difficulty)

        # Display results
        self._display_solve_result(solver_type, result)

    def _solve_all(self) -> None:
        """Solve the current puzzle with all solvers and display comparison."""
        self.console.print("\n  Solving with all algorithms...")

        results = self.solver_manager.solve_all(self.current_puzzle)

        # Record all results
        for solver_type, result in results.items():
            self.evaluator.record(result, self.current_puzzle_id, self.current_difficulty)

        # Display individual results
        for solver_type, result in results.items():
            self._display_solve_result(solver_type, result)

        # Show comparison table
        try:
            comparison = self.evaluator.get_comparison(self.current_puzzle_id)
            render_comparison_table(comparison, console=self.console)
        except KeyError:
            pass

    def _display_solve_result(self, solver_type: SolverType, result) -> None:
        """Display the result of a solve operation.

        Args:
            solver_type: The solver that produced the result.
            result: The SolveResult from the solver.
        """
        self.console.print()
        name = _SOLVER_NAMES[solver_type]

        if result.status == SolveStatus.SOLVED:
            self.console.print(f"  [bold green]✓ {name}: SOLVED[/bold green]")
            self.console.print(
                f"    Time: {result.time_ms} ms  |  "
                f"States: {result.states_explored:,}  |  "
                f"Backtracks: {result.backtracks:,}"
            )
            if result.solved_grid is not None:
                self.console.print()
                print_grid(result.solved_grid, console=self.console)
        elif result.status == SolveStatus.TIMEOUT:
            self.console.print(f"  [bold yellow]⏱ {name}: TIMEOUT[/bold yellow]")
            self.console.print(
                f"    Time: {result.time_ms} ms  |  "
                f"States: {result.states_explored:,}  |  "
                f"Backtracks: {result.backtracks:,}"
            )
        elif result.status == SolveStatus.UNSOLVABLE:
            self.console.print(f"  [bold red]✗ {name}: UNSOLVABLE[/bold red]")
        elif result.status == SolveStatus.FAILED:
            self.console.print(f"  [bold red]✗ {name}: FAILED[/bold red]")
            self.console.print(
                f"    States: {result.states_explored:,}  |  "
                f"Restarts: {result.restarts}"
            )

    def _step_by_step_mode(self) -> None:
        """Handle step-by-step visualization mode."""
        if self.current_puzzle is None:
            self.console.print(
                "\n  [bold yellow]No puzzle generated yet.[/bold yellow] "
                "Please generate a puzzle first (option 1).\n"
            )
            return

        self.console.print()
        self.console.rule("[bold]Step-by-Step Mode[/bold]")
        self.console.print()
        self.console.print("  Select solver algorithm:")
        self.console.print()

        solvers = list(SolverType)
        for i, solver_type in enumerate(solvers, 1):
            self.console.print(f"  [bold]{i}.[/bold] {_SOLVER_NAMES[solver_type]}")
        self.console.print()

        choice = self._get_input(f"Select solver (1-{len(solvers)})")

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(solvers):
                self._show_invalid_input(f"1-{len(solvers)}")
                return
        except ValueError:
            self._show_invalid_input(f"1-{len(solvers)}")
            return

        solver_type = solvers[idx]

        # Ask for delay
        delay_input = self._get_input(
            "Step delay in ms (100-2000, default 500)", default="500"
        )
        try:
            delay_ms = int(delay_input)
        except ValueError:
            delay_ms = 500

        self.console.print(
            f"\n  Running [bold]{_SOLVER_NAMES[solver_type]}[/bold] step-by-step "
            f"(delay: {delay_ms}ms)..."
        )
        self.console.print("  Controls: p=pause, r=resume, s=skip to end\n")

        # Get stepwise generator
        step_gen = self.solver_manager.solve_stepwise(
            self.current_puzzle, solver_type
        )

        # Run visualization
        controller = VisualizationController(
            grid=self.current_puzzle, delay_ms=delay_ms
        )
        result = controller.run(step_gen)

        # Record result
        self.evaluator.record(result, self.current_puzzle_id, self.current_difficulty)

        # Display final result
        self._display_solve_result(solver_type, result)

    def _view_dashboard(self) -> None:
        """Display the comparative analysis dashboard."""
        self.console.print()
        self.console.rule("[bold]Comparative Analysis Dashboard[/bold]")

        # Collect all comparisons and aggregates
        all_results = self.evaluator.get_all_results()

        if not all_results:
            self.console.print(
                "\n  [bold yellow]No results recorded yet.[/bold yellow] "
                "Solve some puzzles first.\n"
            )
            return

        # Build comparison tables for all puzzles
        comparisons = []
        for puzzle_id in all_results:
            try:
                comp = self.evaluator.get_comparison(puzzle_id)
                comparisons.append(comp)
            except KeyError:
                continue

        # Build aggregate stats for each difficulty
        aggregates = {}
        for difficulty in DifficultyLevel:
            aggregate = self.evaluator.get_aggregate(difficulty)
            if aggregate.puzzle_count > 0:
                aggregates[difficulty] = aggregate

        # Render full dashboard
        render_full_dashboard(comparisons, aggregates, console=self.console)

    def _adversarial_mode(self) -> None:
        """Handle adversarial mode (placeholder for task 14)."""
        self.console.print()
        self.console.rule("[bold]Adversarial Mode[/bold]")
        self.console.print(
            "\n  [bold yellow]Adversarial mode is not yet implemented.[/bold yellow]"
        )
        self.console.print("  This feature will be available in a future update.\n")

    def _export_csv(self) -> None:
        """Handle CSV export: prompt for filepath and export results."""
        all_results = self.evaluator.get_all_results()

        if not all_results:
            self.console.print(
                "\n  [bold yellow]No results to export.[/bold yellow] "
                "Solve some puzzles first.\n"
            )
            return

        self.console.print()
        self.console.rule("[bold]Export Results to CSV[/bold]")
        self.console.print()

        filepath = self._get_input(
            "Enter file path for CSV export", default="results.csv"
        )

        try:
            self.evaluator.export_csv(filepath)
            self.console.print(
                f"\n  [bold green]✓ Results exported to:[/bold green] {filepath}\n"
            )
        except Exception as e:
            self.console.print(
                f"\n  [bold red]Error:[/bold red] Failed to export CSV: {e}\n"
            )

    def _get_input(self, prompt: str, default: Optional[str] = None) -> str:
        """Get user input with a formatted prompt.

        Args:
            prompt: The prompt message to display.
            default: Optional default value shown in brackets.

        Returns:
            The user's input string, stripped of whitespace.
            Returns the default if input is empty and default is provided.
        """
        if default:
            display_prompt = f"  {prompt} [{default}]: "
        else:
            display_prompt = f"  {prompt}: "

        try:
            value = input(display_prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return default or ""

        if not value and default:
            return default
        return value

    def _show_invalid_input(self, valid_range: str) -> None:
        """Display an error message for invalid input.

        Args:
            valid_range: Description of valid options (e.g., "1-7").
        """
        self.console.print(
            f"\n  [bold red]Invalid input.[/bold red] "
            f"Please enter a valid option ({valid_range}).\n"
        )
