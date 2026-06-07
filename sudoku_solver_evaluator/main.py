import sys
from rich.console import Console
from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.ui.cli import CLI

def main() -> None:
    # Entry point for CLI mode: prepare components and run the CLI.
    console = Console()
    generator = PuzzleGenerator()
    solver_manager = SolverManager()
    evaluator = PerformanceEvaluator()
    cli = CLI(generator=generator, solver_manager=solver_manager, evaluator=evaluator, console=console)
    cli.run()
if __name__ == '__main__':
    if '--gui' in sys.argv:
        from sudoku_solver_evaluator.gui import run_gui
        run_gui()
    else:
        main()