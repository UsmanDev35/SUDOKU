from __future__ import annotations
import os
import time
import uuid
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from sudoku_solver_evaluator.adversarial.race import RaceController
from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.ui.dashboard import render_aggregate_table, render_comparison_table, render_full_dashboard, render_performance_chart
from sudoku_solver_evaluator.ui.display import print_grid
from sudoku_solver_evaluator.ui.visualization import VisualizationController
_SOLVER_NAMES: dict[SolverType, str] = {SolverType.BACKTRACKING: 'Backtracking Search', SolverType.INFORMED: 'Informed (AC-3 + MRV + Degree)', SolverType.LOCAL_SEARCH: 'Simulated Annealing', SolverType.FORWARD_CHECKING: 'Forward Checking'}
_DIFFICULTY_NAMES: dict[DifficultyLevel, str] = {DifficultyLevel.EASY: 'Easy (36-45 clues)', DifficultyLevel.MEDIUM: 'Medium (27-35 clues)', DifficultyLevel.HARD: 'Hard (22-26 clues)', DifficultyLevel.EXPERT: 'Expert (17-21 clues)'}

class CLI:

    def __init__(self, generator: PuzzleGenerator, solver_manager: SolverManager, evaluator: PerformanceEvaluator, console: Optional[Console]=None) -> None:
        self.generator = generator
        self.solver_manager = solver_manager
        self.evaluator = evaluator
        self.console = console or Console()
        self.current_puzzle: Optional[Grid] = None
        self.current_difficulty: Optional[DifficultyLevel] = None
        self.current_puzzle_id: Optional[str] = None

    def run(self) -> None:
        self.console.print()
        self.console.print(Panel('[bold cyan]AI-Powered Multi-Level Sudoku Solver and Evaluator[/bold cyan]', border_style='bright_blue'))
        while True:
            self._print_main_menu()
            choice = self._get_input('Select an option')
            if choice == '1':
                self._generate_puzzle()
            elif choice == '2':
                self._choose_solver()
            elif choice == '3':
                self._step_by_step_mode()
            elif choice == '4':
                self._view_dashboard()
            elif choice == '5':
                self._adversarial_mode()
            elif choice == '6':
                self._export_csv()
            elif choice == '7':
                self.console.print('\n[bold green]Goodbye![/bold green]\n')
                break
            else:
                self._show_invalid_input('1-7')

    def _print_main_menu(self) -> None:
        self.console.print()
        self.console.rule('[bold cyan]Main Menu[/bold cyan]')
        self.console.print()
        self.console.print('  [bold]1.[/bold] Generate Puzzle')
        self.console.print('  [bold]2.[/bold] Solve Puzzle')
        self.console.print('  [bold]3.[/bold] Step-by-Step Mode')
        self.console.print('  [bold]4.[/bold] View Dashboard')
        self.console.print('  [bold]5.[/bold] Adversarial Mode')
        self.console.print('  [bold]6.[/bold] Export Results to CSV')
        self.console.print('  [bold]7.[/bold] Exit')
        self.console.print()

    def _generate_puzzle(self) -> None:
        self.console.print()
        self.console.rule('[bold]Generate Puzzle[/bold]')
        self.console.print()
        self.console.print('  Select difficulty level:')
        self.console.print()
        difficulties = list(DifficultyLevel)
        for i, diff in enumerate(difficulties, 1):
            self.console.print(f'  [bold]{i}.[/bold] {_DIFFICULTY_NAMES[diff]}')
        self.console.print()
        choice = self._get_input('Select difficulty (1-4)')
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(difficulties):
                self._show_invalid_input('1-4')
                return
        except ValueError:
            self._show_invalid_input('1-4')
            return
        difficulty = difficulties[idx]
        self.console.print(f'\n  Generating [bold]{difficulty.value}[/bold] puzzle...')
        try:
            puzzle = self.generator.generate(difficulty)
        except TimeoutError:
            self.console.print('\n  [bold red]Error:[/bold red] Puzzle generation timed out. Please try again.')
            return
        self.current_puzzle = puzzle
        self.current_difficulty = difficulty
        self.current_puzzle_id = str(uuid.uuid4())[:8]
        self.console.print(f'\n  Puzzle generated! ID: [bold]{self.current_puzzle_id}[/bold]  Filled cells: [bold]{puzzle.count_filled()}[/bold]')
        self.console.print()
        print_grid(puzzle, console=self.console)

    def _choose_solver(self) -> None:
        if self.current_puzzle is None:
            self.console.print('\n  [bold yellow]No puzzle generated yet.[/bold yellow] Please generate a puzzle first (option 1).\n')
            return
        self.console.print()
        self.console.rule('[bold]Solve Puzzle[/bold]')
        self.console.print()
        self.console.print('  Select solver algorithm:')
        self.console.print()
        solvers = list(SolverType)
        for i, solver_type in enumerate(solvers, 1):
            self.console.print(f'  [bold]{i}.[/bold] {_SOLVER_NAMES[solver_type]}')
        self.console.print(f'  [bold]{len(solvers) + 1}.[/bold] Run All Solvers')
        self.console.print()
        choice = self._get_input(f'Select solver (1-{len(solvers) + 1})')
        try:
            idx = int(choice) - 1
            if idx < 0 or idx > len(solvers):
                self._show_invalid_input(f'1-{len(solvers) + 1}')
                return
        except ValueError:
            self._show_invalid_input(f'1-{len(solvers) + 1}')
            return
        if idx == len(solvers):
            self._solve_all()
        else:
            solver_type = solvers[idx]
            self._solve_single(solver_type)

    def _solve_single(self, solver_type: SolverType) -> None:
        self.console.print(f'\n  Solving with [bold]{_SOLVER_NAMES[solver_type]}[/bold]...')
        result = self.solver_manager.solve(self.current_puzzle, solver_type)
        self.evaluator.record(result, self.current_puzzle_id, self.current_difficulty)
        self._display_solve_result(solver_type, result)

    def _solve_all(self) -> None:
        self.console.print('\n  Solving with all algorithms...')
        results = self.solver_manager.solve_all(self.current_puzzle)
        for solver_type, result in results.items():
            self.evaluator.record(result, self.current_puzzle_id, self.current_difficulty)
        for solver_type, result in results.items():
            self._display_solve_result(solver_type, result)
        try:
            comparison = self.evaluator.get_comparison(self.current_puzzle_id)
            render_comparison_table(comparison, console=self.console)
        except KeyError:
            pass

    def _display_solve_result(self, solver_type: SolverType, result) -> None:
        self.console.print()
        name = _SOLVER_NAMES[solver_type]
        if result.status == SolveStatus.SOLVED:
            self.console.print(f'  [bold green][SOLVED] {name}[/bold green]')
            self.console.print(f'    Time: {result.time_ms} ms  |  States: {result.states_explored:,}  |  Backtracks: {result.backtracks:,}')
            if result.solved_grid is not None:
                self.console.print()
                print_grid(result.solved_grid, console=self.console)
        elif result.status == SolveStatus.TIMEOUT:
            self.console.print(f'  [bold yellow][TIMEOUT] {name}[/bold yellow]')
            self.console.print(f'    Time: {result.time_ms} ms  |  States: {result.states_explored:,}  |  Backtracks: {result.backtracks:,}')
        elif result.status == SolveStatus.UNSOLVABLE:
            self.console.print(f'  [bold red][UNSOLVABLE] {name}[/bold red]')
        elif result.status == SolveStatus.FAILED:
            self.console.print(f'  [bold red][FAILED] {name}[/bold red]')
            self.console.print(f'    States: {result.states_explored:,}  |  Restarts: {result.restarts}')

    def _step_by_step_mode(self) -> None:
        if self.current_puzzle is None:
            self.console.print('\n  [bold yellow]No puzzle generated yet.[/bold yellow] Please generate a puzzle first (option 1).\n')
            return
        self.console.print()
        self.console.rule('[bold]Step-by-Step Mode[/bold]')
        self.console.print()
        self.console.print('  Select solver algorithm:')
        self.console.print()
        solvers = list(SolverType)
        for i, solver_type in enumerate(solvers, 1):
            self.console.print(f'  [bold]{i}.[/bold] {_SOLVER_NAMES[solver_type]}')
        self.console.print()
        choice = self._get_input(f'Select solver (1-{len(solvers)})')
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(solvers):
                self._show_invalid_input(f'1-{len(solvers)}')
                return
        except ValueError:
            self._show_invalid_input(f'1-{len(solvers)}')
            return
        solver_type = solvers[idx]
        delay_input = self._get_input('Step delay in ms (50-2000, default 200)', default='200')
        try:
            delay_ms = max(50, min(2000, int(delay_input)))
        except ValueError:
            delay_ms = 200
        self.console.print(f'\n  Running [bold]{_SOLVER_NAMES[solver_type]}[/bold] step-by-step (delay: {delay_ms}ms)...')
        self.console.print('  Press Ctrl+C to skip to end.\n')
        time.sleep(1)
        step_gen = self.solver_manager.solve_stepwise(self.current_puzzle, solver_type)
        result = self._run_step_animation(step_gen, delay_ms)
        self.evaluator.record(result, self.current_puzzle_id, self.current_difficulty)
        self._display_solve_result(solver_type, result)

    def _run_step_animation(self, step_generator, delay_ms: int):
        from sudoku_solver_evaluator.models.enums import StepType
        from sudoku_solver_evaluator.models.metrics import SolveResult
        working_grid = self.current_puzzle.copy()
        skipping = False
        try:
            while True:
                try:
                    step_event = next(step_generator)
                except StopIteration as e:
                    result = e.value
                    break
                if step_event.step_type == StepType.ASSIGN:
                    working_grid.set_value(step_event.row, step_event.col, step_event.value)
                elif step_event.step_type == StepType.BACKTRACK:
                    working_grid.clear_value(step_event.row, step_event.col)
                elif step_event.step_type == StepType.PROPAGATE:
                    if step_event.value is not None:
                        working_grid.set_value(step_event.row, step_event.col, step_event.value)
                if not skipping:
                    try:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        print('=' * 50)
                        print('  STEP-BY-STEP SOLVING')
                        print('=' * 50)
                        if step_event.step_type == StepType.ASSIGN:
                            print(f'  ASSIGN: Cell ({step_event.row + 1},{step_event.col + 1}) = {step_event.value}')
                        elif step_event.step_type == StepType.BACKTRACK:
                            print(f'  *** BACKTRACK *** Cell ({step_event.row + 1},{step_event.col + 1}) cleared')
                        elif step_event.step_type == StepType.SWAP:
                            print(f'  SWAP: Cell ({step_event.row + 1},{step_event.col + 1})')
                        elif step_event.step_type == StepType.PROPAGATE:
                            print(f'  PROPAGATE: Cell ({step_event.row + 1},{step_event.col + 1}) = {step_event.value}')
                        print(f'  States: {step_event.states_explored}  |  Backtracks: {step_event.backtracks}')
                        print('=' * 50)
                        self._print_simple_grid(working_grid, step_event)
                        time.sleep(delay_ms / 1000.0)
                    except KeyboardInterrupt:
                        skipping = True
                        print('\n  Skipping to end...')
        except KeyboardInterrupt:
            skipping = True
            try:
                while True:
                    step_event = next(step_generator)
                    if step_event.step_type == StepType.ASSIGN:
                        working_grid.set_value(step_event.row, step_event.col, step_event.value)
                    elif step_event.step_type == StepType.BACKTRACK:
                        working_grid.clear_value(step_event.row, step_event.col)
            except StopIteration as e:
                result = e.value
        return result

    def _print_simple_grid(self, grid: Grid, step_event=None) -> None:
        from sudoku_solver_evaluator.models.enums import StepType
        highlight_row = step_event.row if step_event else -1
        highlight_col = step_event.col if step_event else -1
        is_backtrack = step_event and step_event.step_type == StepType.BACKTRACK
        print()
        print('     1   2   3    4   5   6    7   8   9')
        print('   +-----------+-----------+-----------+')
        for row in range(9):
            if row > 0 and row % 3 == 0:
                print('   +-----------+-----------+-----------+')
            line = f' {row + 1} |'
            for col in range(9):
                if col > 0 and col % 3 == 0:
                    line += '|'
                cell = grid.get_cell(row, col)
                if row == highlight_row and col == highlight_col:
                    if is_backtrack:
                        marker = ' X '
                    elif cell.value is not None:
                        marker = f'[{cell.value}]'
                    else:
                        marker = '[.]'
                elif cell.value is not None:
                    if cell.is_fixed:
                        marker = f' {cell.value} '
                    else:
                        marker = f' {cell.value} '
                else:
                    marker = ' . '
                line += marker
            line += '|'
            print(line)
        print('   +-----------+-----------+-----------+')

    def _view_dashboard(self) -> None:
        self.console.print()
        self.console.rule('[bold]Comparative Analysis Dashboard[/bold]')
        all_results = self.evaluator.get_all_results()
        if not all_results:
            self.console.print('\n  [bold yellow]No results recorded yet.[/bold yellow] Solve some puzzles first.\n')
            return
        comparisons = []
        for puzzle_id in all_results:
            try:
                comp = self.evaluator.get_comparison(puzzle_id)
                comparisons.append(comp)
            except KeyError:
                continue
        aggregates = {}
        for difficulty in DifficultyLevel:
            aggregate = self.evaluator.get_aggregate(difficulty)
            if aggregate.puzzle_count > 0:
                aggregates[difficulty] = aggregate
        render_full_dashboard(comparisons, aggregates, console=self.console)

    def _adversarial_mode(self) -> None:
        self.console.print()
        self.console.rule('[bold]Adversarial Mode[/bold]')
        self.console.print()
        self.console.print('  Select two different solvers to race against each other.')
        self.console.print()
        solvers = list(SolverType)
        for i, solver_type in enumerate(solvers, 1):
            self.console.print(f'  [bold]{i}.[/bold] {_SOLVER_NAMES[solver_type]}')
        self.console.print()
        choice_a = self._get_input(f'Select first solver (1-{len(solvers)})')
        try:
            idx_a = int(choice_a) - 1
            if idx_a < 0 or idx_a >= len(solvers):
                self._show_invalid_input(f'1-{len(solvers)}')
                return
        except ValueError:
            self._show_invalid_input(f'1-{len(solvers)}')
            return
        choice_b = self._get_input(f'Select second solver (1-{len(solvers)})')
        try:
            idx_b = int(choice_b) - 1
            if idx_b < 0 or idx_b >= len(solvers):
                self._show_invalid_input(f'1-{len(solvers)}')
                return
        except ValueError:
            self._show_invalid_input(f'1-{len(solvers)}')
            return
        if idx_a == idx_b:
            self.console.print('\n  [bold red]Error:[/bold red] Please select two different solvers.\n')
            return
        solver_a = solvers[idx_a]
        solver_b = solvers[idx_b]
        self.console.print('\n  Generating a Medium puzzle for the race...')
        try:
            puzzle = self.generator.generate(DifficultyLevel.MEDIUM)
        except TimeoutError:
            self.console.print('\n  [bold red]Error:[/bold red] Puzzle generation timed out. Please try again.')
            return
        self.console.print(f'  Puzzle ready! Filled cells: [bold]{puzzle.count_filled()}[/bold]')
        self.console.print()
        print_grid(puzzle, console=self.console)
        self.console.print(f'\n  Racing: [bold]{_SOLVER_NAMES[solver_a]}[/bold] vs [bold]{_SOLVER_NAMES[solver_b]}[/bold]...')
        self.console.print('  Please wait...\n')
        race_controller = RaceController(solver_manager=self.solver_manager)
        race_result = race_controller.start_race(grid=puzzle, solver_a=solver_a, solver_b=solver_b, timeout=60.0)
        self.console.print()
        self.console.rule('[bold cyan]Race Results[/bold cyan]')
        self.console.print()
        res_a = race_result.solver_a_result
        self.console.print(f'  [bold]{_SOLVER_NAMES[solver_a]}[/bold]:')
        self.console.print(f'    Status: {res_a.status.value}  |  Time: {res_a.time_ms}ms  |  States: {res_a.states_explored:,}  |  Backtracks: {res_a.backtracks:,}')
        res_b = race_result.solver_b_result
        self.console.print(f'\n  [bold]{_SOLVER_NAMES[solver_b]}[/bold]:')
        self.console.print(f'    Status: {res_b.status.value}  |  Time: {res_b.time_ms}ms  |  States: {res_b.states_explored:,}  |  Backtracks: {res_b.backtracks:,}')
        self.console.print()
        if race_result.winner is not None:
            winner_name = _SOLVER_NAMES[race_result.winner]
            self.console.print(f'  [bold green]WINNER: {winner_name}[/bold green] (by {race_result.time_difference_ms}ms)')
        elif res_a.status == SolveStatus.SOLVED and res_b.status == SolveStatus.SOLVED:
            self.console.print(f'  [bold yellow]TIE![/bold yellow] Both solved within {race_result.time_difference_ms}ms of each other.')
        elif res_a.status == SolveStatus.TIMEOUT and res_b.status == SolveStatus.TIMEOUT:
            self.console.print('  [bold red]Both solvers timed out.[/bold red] No winner.')
        else:
            self.console.print('  [bold yellow]No winner.[/bold yellow] Neither solver completed successfully.')
        self.console.print()

    def _export_csv(self) -> None:
        all_results = self.evaluator.get_all_results()
        if not all_results:
            self.console.print('\n  [bold yellow]No results to export.[/bold yellow] Solve some puzzles first.\n')
            return
        self.console.print()
        self.console.rule('[bold]Export Results to CSV[/bold]')
        self.console.print()
        filepath = self._get_input('Enter file path for CSV export', default='results.csv')
        try:
            self.evaluator.export_csv(filepath)
            self.console.print(f'\n  [bold green]Results exported to:[/bold green] {filepath}\n')
        except Exception as e:
            self.console.print(f'\n  [bold red]Error:[/bold red] Failed to export CSV: {e}\n')

    def _get_input(self, prompt: str, default: Optional[str]=None) -> str:
        if default:
            display_prompt = f'  {prompt} [{default}]: '
        else:
            display_prompt = f'  {prompt}: '
        try:
            value = input(display_prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return default or ''
        if not value and default:
            return default
        return value

    def _show_invalid_input(self, valid_range: str) -> None:
        self.console.print(f'\n  [bold red]Invalid input.[/bold red] Please enter a valid option ({valid_range}).\n')