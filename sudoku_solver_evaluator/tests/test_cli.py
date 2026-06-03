"""Unit tests for the CLI menu and navigation.

Tests that the CLI handles menu navigation, invalid input, and
integrates correctly with the generator, solver manager, and evaluator.
"""

from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
from rich.console import Console

from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid, Cell
from sudoku_solver_evaluator.models.metrics import SolveResult
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.ui.cli import CLI


def _make_console() -> Console:
    """Create a Console that writes to a StringIO buffer."""
    return Console(file=StringIO(), force_terminal=True, width=120)


def _make_cli(console: Console | None = None) -> CLI:
    """Create a CLI instance with real components and a buffered console."""
    if console is None:
        console = _make_console()
    generator = PuzzleGenerator()
    solver_manager = SolverManager()
    evaluator = PerformanceEvaluator()
    return CLI(
        generator=generator,
        solver_manager=solver_manager,
        evaluator=evaluator,
        console=console,
    )


def _make_simple_grid() -> Grid:
    """Create a simple almost-complete grid for testing (one empty cell)."""
    # A valid complete grid with one cell emptied
    values = [
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
    # Make cell (0,0) empty
    values[0][0] = 0
    return Grid.from_2d_list(values)


class TestCLIExit:
    """Test that the CLI exits cleanly on option 7."""

    @patch("builtins.input", side_effect=["7"])
    def test_exit_on_7(self, mock_input):
        """CLI should exit cleanly when user selects option 7."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Goodbye" in output


class TestCLIInvalidInput:
    """Test invalid input handling."""

    @patch("builtins.input", side_effect=["0", "7"])
    def test_invalid_main_menu_input_zero(self, mock_input):
        """CLI shows error for invalid input 0 then continues."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Invalid input" in output

    @patch("builtins.input", side_effect=["abc", "7"])
    def test_invalid_main_menu_input_text(self, mock_input):
        """CLI shows error for non-numeric input then continues."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Invalid input" in output

    @patch("builtins.input", side_effect=["9", "7"])
    def test_invalid_main_menu_input_out_of_range(self, mock_input):
        """CLI shows error for out-of-range input then continues."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Invalid input" in output


class TestCLIGeneratePuzzle:
    """Test puzzle generation menu flow."""

    @patch("builtins.input", side_effect=["1", "1", "7"])
    def test_generate_easy_puzzle(self, mock_input):
        """CLI generates an easy puzzle and displays it."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Puzzle generated" in output
        assert cli.current_puzzle is not None
        assert cli.current_difficulty == DifficultyLevel.EASY

    @patch("builtins.input", side_effect=["1", "5", "7"])
    def test_generate_invalid_difficulty(self, mock_input):
        """CLI shows error for invalid difficulty selection."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Invalid input" in output

    @patch("builtins.input", side_effect=["1", "abc", "7"])
    def test_generate_non_numeric_difficulty(self, mock_input):
        """CLI shows error for non-numeric difficulty input."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Invalid input" in output


class TestCLISolvePuzzle:
    """Test puzzle solving menu flow."""

    @patch("builtins.input", side_effect=["2", "7"])
    def test_solve_without_puzzle(self, mock_input):
        """CLI warns user if no puzzle has been generated."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "No puzzle generated yet" in output

    @patch("builtins.input", side_effect=["2", "1", "7"])
    def test_solve_single_solver(self, mock_input):
        """CLI solves with a single solver after puzzle is loaded."""
        console = _make_console()
        cli = _make_cli(console)
        # Pre-load a simple puzzle
        cli.current_puzzle = _make_simple_grid()
        cli.current_difficulty = DifficultyLevel.EASY
        cli.current_puzzle_id = "test-001"
        cli.run()
        output = console.file.getvalue()
        assert "SOLVED" in output

    @patch("builtins.input", side_effect=["2", "5", "7"])
    def test_solve_all_solvers(self, mock_input):
        """CLI solves with all solvers when option 5 (all) is selected."""
        console = _make_console()
        cli = _make_cli(console)
        # Pre-load a simple puzzle
        cli.current_puzzle = _make_simple_grid()
        cli.current_difficulty = DifficultyLevel.EASY
        cli.current_puzzle_id = "test-002"
        cli.run()
        output = console.file.getvalue()
        # All 4 solvers should produce results
        assert "Backtracking" in output or "SOLVED" in output

    @patch("builtins.input", side_effect=["2", "0", "7"])
    def test_solve_invalid_solver_choice(self, mock_input):
        """CLI shows error for invalid solver selection."""
        console = _make_console()
        cli = _make_cli(console)
        cli.current_puzzle = _make_simple_grid()
        cli.current_difficulty = DifficultyLevel.EASY
        cli.current_puzzle_id = "test-003"
        cli.run()
        output = console.file.getvalue()
        assert "Invalid input" in output


class TestCLIStepByStep:
    """Test step-by-step mode menu flow."""

    @patch("builtins.input", side_effect=["3", "7"])
    def test_stepbystep_without_puzzle(self, mock_input):
        """CLI warns user if no puzzle generated for step-by-step mode."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "No puzzle generated yet" in output


class TestCLIDashboard:
    """Test dashboard view menu flow."""

    @patch("builtins.input", side_effect=["4", "7"])
    def test_dashboard_no_results(self, mock_input):
        """CLI shows message when no results recorded for dashboard."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "No results recorded yet" in output


class TestCLIAdversarialMode:
    """Test adversarial mode placeholder."""

    @patch("builtins.input", side_effect=["5", "7"])
    def test_adversarial_not_implemented(self, mock_input):
        """CLI shows placeholder message for adversarial mode."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "not yet implemented" in output


class TestCLIExportCSV:
    """Test CSV export menu flow."""

    @patch("builtins.input", side_effect=["6", "7"])
    def test_export_no_results(self, mock_input):
        """CLI shows message when no results to export."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "No results to export" in output


class TestCLIMenuDisplay:
    """Test that main menu displays all expected options."""

    @patch("builtins.input", side_effect=["7"])
    def test_menu_shows_all_options(self, mock_input):
        """CLI displays all 7 menu options."""
        console = _make_console()
        cli = _make_cli(console)
        cli.run()
        output = console.file.getvalue()
        assert "Generate Puzzle" in output
        assert "Solve Puzzle" in output
        assert "Step-by-Step Mode" in output
        assert "View Dashboard" in output
        assert "Adversarial Mode" in output
        assert "Export Results to CSV" in output
        assert "Exit" in output
