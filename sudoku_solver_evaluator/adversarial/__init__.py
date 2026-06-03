"""Adversarial mode with concurrent solver racing.

Runs two solvers concurrently using threading and determines
the winner based on completion time.
"""

from sudoku_solver_evaluator.adversarial.race import RaceController

__all__ = ["RaceController"]
