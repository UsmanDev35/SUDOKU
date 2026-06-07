from __future__ import annotations
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional
from sudoku_solver_evaluator.evaluator.performance import PerformanceEvaluator
from sudoku_solver_evaluator.generator.puzzle_generator import PuzzleGenerator
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolveStatus, SolverType, StepType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import SolveResult, StepEvent
from sudoku_solver_evaluator.solvers import SolverManager
from sudoku_solver_evaluator.adversarial.race import RaceController
BOX_COLORS = ['#FFFFFF', '#F0F0FF', '#FFFFFF', '#F0F0FF', '#FFFFFF', '#F0F0FF', '#FFFFFF', '#F0F0FF', '#FFFFFF']
CELL_SIZE = 50
GRID_SIZE = CELL_SIZE * 9
SOLVER_NAMES = {SolverType.BACKTRACKING: 'Backtracking', SolverType.INFORMED: 'Informed (AC-3+MRV)', SolverType.LOCAL_SEARCH: 'Simulated Annealing', SolverType.FORWARD_CHECKING: 'Forward Checking'}

class SudokuGUI:

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Sudoku Solver & Evaluator')
        self.root.resizable(False, False)
        self.generator = PuzzleGenerator()
        self.solver_manager = SolverManager()
        self.evaluator = PerformanceEvaluator()
        self.current_puzzle: Optional[Grid] = None
        self.current_solution: Optional[Grid] = None
        self.animating = False
        self.animation_id: Optional[str] = None
        self.step_events: list[StepEvent] = []
        self.step_index = 0
        self.difficulty_var = tk.StringVar(value='easy')
        self.solver_var = tk.StringVar(value='backtracking')
        self.speed_var = tk.IntVar(value=100)
        self._build_ui()

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky='nsew')
        self._build_grid_panel(main_frame)
        self._build_control_panel(main_frame)
        self._build_status_bar()

    def _build_grid_panel(self, parent: ttk.Frame) -> None:
        grid_frame = ttk.LabelFrame(parent, text='Sudoku Grid', padding=5)
        grid_frame.grid(row=0, column=0, padx=(0, 10), sticky='n')
        self.canvas = tk.Canvas(grid_frame, width=GRID_SIZE + 4, height=GRID_SIZE + 4, bg='white', highlightthickness=0)
        self.canvas.pack()
        self._draw_empty_grid()

    def _build_control_panel(self, parent: ttk.Frame) -> None:
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=0, column=1, sticky='n')
        diff_frame = ttk.LabelFrame(control_frame, text='Difficulty', padding=5)
        diff_frame.pack(fill='x', pady=(0, 5))
        difficulties = [('Easy', 'easy'), ('Medium', 'medium'), ('Hard', 'hard'), ('Expert', 'expert')]
        for text, value in difficulties:
            ttk.Radiobutton(diff_frame, text=text, variable=self.difficulty_var, value=value).pack(anchor='w')
        self.btn_generate = ttk.Button(control_frame, text='Generate Puzzle', command=self._on_generate)
        self.btn_generate.pack(fill='x', pady=5)
        solver_frame = ttk.LabelFrame(control_frame, text='Solver', padding=5)
        solver_frame.pack(fill='x', pady=(0, 5))
        solvers = [('Backtracking', 'backtracking'), ('Informed (AC-3+MRV)', 'informed'), ('Simulated Annealing', 'local_search'), ('Forward Checking', 'forward_checking')]
        for text, value in solvers:
            ttk.Radiobutton(solver_frame, text=text, variable=self.solver_var, value=value).pack(anchor='w')
        self.btn_solve = ttk.Button(control_frame, text='Solve', command=self._on_solve)
        self.btn_solve.pack(fill='x', pady=2)
        self.btn_animate = ttk.Button(control_frame, text='Animate', command=self._on_animate)
        self.btn_animate.pack(fill='x', pady=2)
        speed_frame = ttk.LabelFrame(control_frame, text='Animation Speed (ms)', padding=5)
        speed_frame.pack(fill='x', pady=(0, 5))
        self.speed_slider = ttk.Scale(speed_frame, from_=10, to=500, variable=self.speed_var, orient='horizontal')
        self.speed_slider.pack(fill='x')
        self.speed_label = ttk.Label(speed_frame, text='100ms')
        self.speed_label.pack()
        self.speed_var.trace_add('write', self._update_speed_label)
        self.btn_stop = ttk.Button(control_frame, text='Stop Animation', command=self._on_stop, state='disabled')
        self.btn_stop.pack(fill='x', pady=2)
        self.btn_run_all = ttk.Button(control_frame, text='Run All Solvers', command=self._on_run_all)
        self.btn_run_all.pack(fill='x', pady=2)
        self.btn_race = ttk.Button(control_frame, text='Adversarial Race', command=self._on_race)
        self.btn_race.pack(fill='x', pady=2)
        results_frame = ttk.LabelFrame(control_frame, text='Results', padding=5)
        results_frame.pack(fill='both', expand=True, pady=(5, 0))
        self.results_text = tk.Text(results_frame, width=35, height=10, font=('Consolas', 9))
        self.results_text.pack(fill='both', expand=True)

    def _build_status_bar(self) -> None:
        self.status_var = tk.StringVar(value='Ready')
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w', padding=(5, 2))
        status_bar.grid(row=1, column=0, sticky='ew')

    def _update_speed_label(self, *args) -> None:
        self.speed_label.config(text=f'{self.speed_var.get()}ms')

    def _draw_empty_grid(self) -> None:
        self.canvas.delete('all')
        for box_row in range(3):
            for box_col in range(3):
                box_idx = box_row * 3 + box_col
                x1 = box_col * 3 * CELL_SIZE + 2
                y1 = box_row * 3 * CELL_SIZE + 2
                x2 = x1 + 3 * CELL_SIZE
                y2 = y1 + 3 * CELL_SIZE
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=BOX_COLORS[box_idx], outline='')
        for i in range(10):
            x = i * CELL_SIZE + 2
            width = 3 if i % 3 == 0 else 1
            self.canvas.create_line(x, 2, x, GRID_SIZE + 2, width=width)
            self.canvas.create_line(2, x, GRID_SIZE + 2, x, width=width)

    def _draw_grid(self, grid: Grid, solved_grid: Optional[Grid]=None, highlight_cell: Optional[tuple[int, int]]=None, highlight_color: str='lightgreen') -> None:
        self._draw_empty_grid()
        display_grid = solved_grid if solved_grid else grid
        for row in range(9):
            for col in range(9):
                x = col * CELL_SIZE + CELL_SIZE // 2 + 2
                y = row * CELL_SIZE + CELL_SIZE // 2 + 2
                if highlight_cell and (row, col) == highlight_cell:
                    cx1 = col * CELL_SIZE + 3
                    cy1 = row * CELL_SIZE + 3
                    cx2 = cx1 + CELL_SIZE - 2
                    cy2 = cy1 + CELL_SIZE - 2
                    self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill=highlight_color, outline='')
                cell = display_grid.get_cell(row, col)
                if cell.value is not None:
                    original_cell = grid.get_cell(row, col)
                    if original_cell.is_fixed:
                        color = 'black'
                        font = ('Arial', 16, 'bold')
                    else:
                        color = 'blue'
                        font = ('Arial', 16)
                    self.canvas.create_text(x, y, text=str(cell.value), fill=color, font=font)

    def _disable_buttons(self) -> None:
        self.btn_generate.config(state='disabled')
        self.btn_solve.config(state='disabled')
        self.btn_animate.config(state='disabled')
        self.btn_run_all.config(state='disabled')
        self.btn_race.config(state='disabled')

    def _enable_buttons(self) -> None:
        self.btn_generate.config(state='normal')
        self.btn_solve.config(state='normal')
        self.btn_animate.config(state='normal')
        self.btn_run_all.config(state='normal')
        self.btn_race.config(state='normal')
        self.btn_stop.config(state='disabled')

    def _on_generate(self) -> None:
        self._disable_buttons()
        self.status_var.set('Generating...')
        self.current_solution = None
        self.results_text.delete('1.0', tk.END)
        diff_str = self.difficulty_var.get()
        difficulty = DifficultyLevel(diff_str)

        def generate():
            try:
                puzzle = self.generator.generate(difficulty, timeout=60.0)
                self.root.after(0, lambda: self._on_generate_done(puzzle))
            except TimeoutError:
                self.root.after(0, lambda: self._on_generate_error())
        threading.Thread(target=generate, daemon=True).start()

    def _on_generate_done(self, puzzle: Grid) -> None:
        self.current_puzzle = puzzle
        self._draw_grid(puzzle)
        filled = puzzle.count_filled()
        self.status_var.set(f'Puzzle generated | Filled cells: {filled}')
        self._enable_buttons()

    def _on_generate_error(self) -> None:
        self.status_var.set('Generation timed out')
        self._enable_buttons()
        messagebox.showwarning('Timeout', 'Puzzle generation timed out. Try again.')

    def _on_solve(self) -> None:
        if self.current_puzzle is None:
            messagebox.showinfo('No Puzzle', 'Generate a puzzle first.')
            return
        self._disable_buttons()
        solver_type = SolverType(self.solver_var.get())
        self.status_var.set(f'Solving with {SOLVER_NAMES[solver_type]}...')

        def solve():
            result = self.solver_manager.solve(self.current_puzzle, solver_type)
            self.root.after(0, lambda: self._on_solve_done(result))
        threading.Thread(target=solve, daemon=True).start()

    def _on_solve_done(self, result: SolveResult) -> None:
        if result.status == SolveStatus.SOLVED and result.solved_grid:
            self.current_solution = result.solved_grid
            self._draw_grid(self.current_puzzle, result.solved_grid)
            self.status_var.set(f'States: {result.states_explored:,} | Backtracks: {result.backtracks:,} | Time: {result.time_ms}ms')
        elif result.status == SolveStatus.TIMEOUT:
            self.status_var.set(f'TIMEOUT after {result.time_ms}ms')
        else:
            self.status_var.set(f'Status: {result.status.value}')
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', f'Solver: {SOLVER_NAMES[result.solver_type]}\nStatus: {result.status.value}\nTime: {result.time_ms}ms\nStates: {result.states_explored:,}\nBacktracks: {result.backtracks:,}\n')
        self._enable_buttons()

    def _on_animate(self) -> None:
        if self.current_puzzle is None:
            messagebox.showinfo('No Puzzle', 'Generate a puzzle first.')
            return
        self._disable_buttons()
        self.btn_stop.config(state='normal')
        self.animating = True
        solver_type = SolverType(self.solver_var.get())
        self.status_var.set(f'Animating {SOLVER_NAMES[solver_type]}...')

        def collect_steps():
            step_gen = self.solver_manager.solve_stepwise(self.current_puzzle, solver_type)
            events = []
            result = None
            try:
                while True:
                    event = next(step_gen)
                    events.append(event)
            except StopIteration as e:
                result = e.value
            self.root.after(0, lambda: self._start_animation(events, result))
        threading.Thread(target=collect_steps, daemon=True).start()

    def _start_animation(self, events: list[StepEvent], result: SolveResult) -> None:
        self.step_events = events
        self.step_index = 0
        self._animation_result = result
        self._draw_grid(self.current_puzzle)
        self._anim_grid = self.current_puzzle.copy()
        self._animate_step()

    def _animate_step(self) -> None:
        if not self.animating or self.step_index >= len(self.step_events):
            self._on_animation_done()
            return
        event = self.step_events[self.step_index]
        self.step_index += 1
        if event.step_type == StepType.ASSIGN:
            self._anim_grid.set_value(event.row, event.col, event.value)
            highlight_color = 'lightgreen'
        elif event.step_type == StepType.BACKTRACK:
            self._anim_grid.clear_value(event.row, event.col)
            highlight_color = '#FF6666'
        elif event.step_type == StepType.PROPAGATE:
            if event.value is not None:
                self._anim_grid.set_value(event.row, event.col, event.value)
            highlight_color = 'lightyellow'
        else:
            highlight_color = 'lightgreen'
        self._draw_grid(self.current_puzzle, self._anim_grid, highlight_cell=(event.row, event.col), highlight_color=highlight_color)
        self.status_var.set(f'States: {event.states_explored:,} | Backtracks: {event.backtracks:,} | Step {self.step_index}/{len(self.step_events)}')
        delay = self.speed_var.get()
        self.animation_id = self.root.after(delay, self._animate_step)

    def _on_animation_done(self) -> None:
        self.animating = False
        result = self._animation_result
        if result and result.status == SolveStatus.SOLVED and result.solved_grid:
            self._draw_grid(self.current_puzzle, result.solved_grid)
            self.status_var.set(f'Done | States: {result.states_explored:,} | Backtracks: {result.backtracks:,} | Time: {result.time_ms}ms')
        else:
            self.status_var.set(f"Animation complete | Status: {(result.status.value if result else 'unknown')}")
        self._enable_buttons()

    def _on_stop(self) -> None:
        self.animating = False
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.status_var.set('Animation stopped')
        self._enable_buttons()

    def _on_run_all(self) -> None:
        if self.current_puzzle is None:
            messagebox.showinfo('No Puzzle', 'Generate a puzzle first.')
            return
        self._disable_buttons()
        self.status_var.set('Solving with all algorithms...')

        def solve_all():
            results = self.solver_manager.solve_all(self.current_puzzle)
            self.root.after(0, lambda: self._on_run_all_done(results))
        threading.Thread(target=solve_all, daemon=True).start()

    def _on_run_all_done(self, results: dict[SolverType, SolveResult]) -> None:
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', 'Algorithm Comparison:\n')
        self.results_text.insert(tk.END, '-' * 34 + '\n')
        for solver_type, result in results.items():
            name = SOLVER_NAMES[solver_type][:15]
            line = f'{name:<15} | {result.status.value:<8} | {result.time_ms:>5}ms | {result.states_explored:>6}st\n'
            self.results_text.insert(tk.END, line)
        for result in results.values():
            if result.status == SolveStatus.SOLVED and result.solved_grid:
                self._draw_grid(self.current_puzzle, result.solved_grid)
                break
        self.status_var.set('All solvers complete')
        self._enable_buttons()

    def _on_race(self) -> None:
        if self.current_puzzle is None:
            messagebox.showinfo('No Puzzle', 'Generate a puzzle first.')
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('Adversarial Race - Select Solvers')
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text='Select Solver A:').grid(row=0, column=0, padx=10, pady=5)
        solver_a_var = tk.StringVar(value='backtracking')
        solvers_list = list(SolverType)
        for i, st in enumerate(solvers_list):
            ttk.Radiobutton(dialog, text=SOLVER_NAMES[st], variable=solver_a_var, value=st.value).grid(row=i + 1, column=0, sticky='w', padx=20)
        ttk.Label(dialog, text='Select Solver B:').grid(row=0, column=1, padx=10, pady=5)
        solver_b_var = tk.StringVar(value='informed')
        for i, st in enumerate(solvers_list):
            ttk.Radiobutton(dialog, text=SOLVER_NAMES[st], variable=solver_b_var, value=st.value).grid(row=i + 1, column=1, sticky='w', padx=20)

        def start_race():
            a = SolverType(solver_a_var.get())
            b = SolverType(solver_b_var.get())
            if a == b:
                messagebox.showwarning('Error', 'Select two different solvers.')
                return
            dialog.destroy()
            self._run_race(a, b)
        ttk.Button(dialog, text='Start Race', command=start_race).grid(row=len(solvers_list) + 1, column=0, columnspan=2, pady=10)

    def _run_race(self, solver_a: SolverType, solver_b: SolverType) -> None:
        self._disable_buttons()
        self.status_var.set(f'Racing: {SOLVER_NAMES[solver_a]} vs {SOLVER_NAMES[solver_b]}...')

        def race():
            controller = RaceController(solver_manager=self.solver_manager)
            result = controller.start_race(grid=self.current_puzzle, solver_a=solver_a, solver_b=solver_b, timeout=60.0)
            self.root.after(0, lambda: self._on_race_done(result))
        threading.Thread(target=race, daemon=True).start()

    def _on_race_done(self, race_result) -> None:
        res_a = race_result.solver_a_result
        res_b = race_result.solver_b_result
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', 'Race Results:\n')
        self.results_text.insert(tk.END, '-' * 34 + '\n')
        self.results_text.insert(tk.END, f'{SOLVER_NAMES[res_a.solver_type]}:\n  {res_a.status.value} | {res_a.time_ms}ms | {res_a.states_explored:,} states\n\n')
        self.results_text.insert(tk.END, f'{SOLVER_NAMES[res_b.solver_type]}:\n  {res_b.status.value} | {res_b.time_ms}ms | {res_b.states_explored:,} states\n\n')
        if race_result.winner:
            winner_name = SOLVER_NAMES[race_result.winner]
            msg = f'WINNER: {winner_name}\n(by {race_result.time_difference_ms}ms)'
            self.results_text.insert(tk.END, msg)
            messagebox.showinfo('Race Result', msg)
        else:
            if res_a.status == SolveStatus.SOLVED and res_b.status == SolveStatus.SOLVED:
                msg = f'TIE! (within {race_result.time_difference_ms}ms)'
            else:
                msg = 'No winner - solvers did not both complete.'
            self.results_text.insert(tk.END, msg)
            messagebox.showinfo('Race Result', msg)
        self.status_var.set('Race complete')
        self._enable_buttons()

def run_gui() -> None:
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()
if __name__ == '__main__':
    run_gui()