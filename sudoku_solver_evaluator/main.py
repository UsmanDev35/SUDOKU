"""Entry point for the AI-Powered Multi-Level Sudoku Solver and Evaluator.

Initializes all components (PuzzleGenerator, SolverManager, PerformanceEvaluator)
and starts the interactive CLI menu loop.

Run with: python -m sudoku_solver_evaluator.main
"""

from rich.console import Console

from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.ui.cli import CLI


def main() -> None:
    """Initialize all components and start the CLI application.

    Creates instances of:
        - PuzzleGenerator: generates puzzles at various difficulty levels
        - SolverManager: manages all four solver implementations
        - PerformanceEvaluator: records and computes performance metrics
        - CLI: interactive menu system using Rich Console

    Then starts the main CLI loop which runs until the user exits.
    """
    console = Console()

    # Initialize core components
    generator = PuzzleGenerator()
    solver_manager = SolverManager()
    evaluator = PerformanceEvaluator()

    # Create and run the CLI
    cli = CLI(
        generator=generator,
        solver_manager=solver_manager,
        evaluator=evaluator,
        console=console,
    )
    cli.run()


if __name__ == "__main__":
    main()
