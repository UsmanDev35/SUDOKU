from __future__ import annotations
import threading
import time
from typing import Optional
from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import RaceResult, RaceStatus, SolveResult
from sudoku_solver_evaluator.solvers import SolverManager

class RaceController:

    def __init__(self, solver_manager: Optional[SolverManager]=None) -> None:
        # Initialize race controller state and threading primitives.
        self._solver_manager = solver_manager or SolverManager()
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._is_running: bool = False
        self._status_a: Optional[RaceStatus] = None
        self._status_b: Optional[RaceStatus] = None
        self._result_a: Optional[SolveResult] = None
        self._result_b: Optional[SolveResult] = None
        self._completion_time_a: Optional[float] = None
        self._completion_time_b: Optional[float] = None
        self._exception_a: Optional[Exception] = None
        self._exception_b: Optional[Exception] = None

    def start_race(self, grid: Grid, solver_a: SolverType, solver_b: SolverType, timeout: float=60.0) -> RaceResult:
        # Start a timed race between two solvers on the same grid and return the RaceResult.
        if solver_a == solver_b:
            raise ValueError(f"Adversarial mode requires two distinct solvers, got '{solver_a.value}' for both.")
        self._cancel_event.clear()
        self._is_running = True
        self._start_time = time.monotonic()
        self._result_a = None
        self._result_b = None
        self._completion_time_a = None
        self._completion_time_b = None
        self._exception_a = None
        self._exception_b = None
        self._status_a = RaceStatus(solver_type=solver_a, states_explored=0, elapsed_ms=0, is_complete=False)
        self._status_b = RaceStatus(solver_type=solver_b, states_explored=0, elapsed_ms=0, is_complete=False)
        thread_a = threading.Thread(target=self._run_solver, args=(grid, solver_a, timeout, 'a'), name=f'RaceSolver-{solver_a.value}', daemon=True)
        thread_b = threading.Thread(target=self._run_solver, args=(grid, solver_b, timeout, 'b'), name=f'RaceSolver-{solver_b.value}', daemon=True)
        thread_a.start()
        thread_b.start()
        self._monitor_race(thread_a, thread_b, timeout)
        self._is_running = False
        if self._result_a is None:
            elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
            if self._exception_a is not None:
                self._result_a = SolveResult(solver_type=solver_a, status=SolveStatus.FAILED, time_ms=elapsed_ms, states_explored=self._status_a.states_explored if self._status_a else 0)
            else:
                self._result_a = SolveResult(solver_type=solver_a, status=SolveStatus.TIMEOUT, time_ms=elapsed_ms, states_explored=self._status_a.states_explored if self._status_a else 0)
        if self._result_b is None:
            elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
            if self._exception_b is not None:
                self._result_b = SolveResult(solver_type=solver_b, status=SolveStatus.FAILED, time_ms=elapsed_ms, states_explored=self._status_b.states_explored if self._status_b else 0)
            else:
                self._result_b = SolveResult(solver_type=solver_b, status=SolveStatus.TIMEOUT, time_ms=elapsed_ms, states_explored=self._status_b.states_explored if self._status_b else 0)
        winner = self._determine_winner(solver_a, solver_b)
        time_difference_ms = abs(self._result_a.time_ms - self._result_b.time_ms)
        return RaceResult(solver_a_type=solver_a, solver_b_type=solver_b, solver_a_result=self._result_a, solver_b_result=self._result_b, winner=winner, time_difference_ms=time_difference_ms)

    def get_live_status(self) -> tuple[RaceStatus, RaceStatus]:
        # Return the current live status snapshots for both racers.
        with self._lock:
            if self._status_a is None or self._status_b is None:
                raise RuntimeError('No race is currently in progress.')
            return (self._status_a, self._status_b)

    def stop(self) -> None:
        # Signal cancellation and mark the race as not running.
        self._cancel_event.set()
        self._is_running = False

    def _run_solver(self, grid: Grid, solver_type: SolverType, timeout: float, identifier: str) -> None:
        # Run a solver in a thread, capture its result/status, and set cancellation on success.
        try:
            result = self._solver_manager.solve(grid, solver_type, timeout=timeout)
            completion_time = time.monotonic()
            with self._lock:
                if identifier == 'a':
                    self._result_a = result
                    self._completion_time_a = completion_time
                    if self._status_a is not None:
                        self._status_a = RaceStatus(solver_type=solver_type, states_explored=result.states_explored, elapsed_ms=result.time_ms, is_complete=True)
                else:
                    self._result_b = result
                    self._completion_time_b = completion_time
                    if self._status_b is not None:
                        self._status_b = RaceStatus(solver_type=solver_type, states_explored=result.states_explored, elapsed_ms=result.time_ms, is_complete=True)
            if result.status == SolveStatus.SOLVED:
                self._cancel_event.set()
        except Exception as e:
            with self._lock:
                if identifier == 'a':
                    self._exception_a = e
                    if self._status_a is not None:
                        elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
                        self._status_a = RaceStatus(solver_type=solver_type, states_explored=self._status_a.states_explored, elapsed_ms=elapsed_ms, is_complete=True)
                else:
                    self._exception_b = e
                    if self._status_b is not None:
                        elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
                        self._status_b = RaceStatus(solver_type=solver_type, states_explored=self._status_b.states_explored, elapsed_ms=elapsed_ms, is_complete=True)

    def _monitor_race(self, thread_a: threading.Thread, thread_b: threading.Thread, timeout: float) -> None:
        # Monitor running race threads, update statuses, and enforce timeout/cancellation.
        poll_interval = 0.1
        while True:
            elapsed = time.monotonic() - self._start_time
            if elapsed >= timeout:
                self._cancel_event.set()
                thread_a.join(timeout=1.0)
                thread_b.join(timeout=1.0)
                break
            elapsed_ms = int(elapsed * 1000)
            with self._lock:
                if self._status_a is not None and (not self._status_a.is_complete):
                    self._status_a = RaceStatus(solver_type=self._status_a.solver_type, states_explored=self._status_a.states_explored, elapsed_ms=elapsed_ms, is_complete=False)
                if self._status_b is not None and (not self._status_b.is_complete):
                    self._status_b = RaceStatus(solver_type=self._status_b.solver_type, states_explored=self._status_b.states_explored, elapsed_ms=elapsed_ms, is_complete=False)
            if not thread_a.is_alive() and (not thread_b.is_alive()):
                break
            if self._cancel_event.is_set():
                thread_a.join(timeout=1.0)
                thread_b.join(timeout=1.0)
                break
            time.sleep(poll_interval)

    def _determine_winner(self, solver_a: SolverType, solver_b: SolverType) -> Optional[SolverType]:
        # Decide which solver (if any) won based on success and timing thresholds.
        result_a = self._result_a
        result_b = self._result_b
        if result_a is None or result_b is None:
            return None
        a_solved = result_a.status == SolveStatus.SOLVED
        b_solved = result_b.status == SolveStatus.SOLVED
        if not a_solved and (not b_solved):
            return None
        if a_solved and (not b_solved):
            return solver_a
        if b_solved and (not a_solved):
            return solver_b
        time_diff = abs(result_a.time_ms - result_b.time_ms)
        if time_diff < 1000:
            return None
        if result_a.time_ms < result_b.time_ms:
            return solver_a
        else:
            return solver_b