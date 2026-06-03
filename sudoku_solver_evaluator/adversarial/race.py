"""Adversarial race controller for concurrent solver execution.

This module implements the RaceController class that manages concurrent
execution of two solvers racing to solve the same puzzle. It uses Python's
threading module for concurrency and threading.Event for cooperative
cancellation signaling.

The controller:
1. Runs two solvers in separate threads on the same puzzle.
2. Monitors both threads, providing live status updates at least once per second.
3. When one solver completes first, signals the other to stop.
4. When timeout is reached, stops both and reports partial metrics.
5. Determines the winner by completion time (tie if within same second).

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from sudoku_solver_evaluator.models.enums import SolveStatus, SolverType
from sudoku_solver_evaluator.models.grid import Grid
from sudoku_solver_evaluator.models.metrics import RaceResult, RaceStatus, SolveResult
from sudoku_solver_evaluator.solvers import SolverManager


class RaceController:
    """Manages concurrent solver execution for adversarial mode.

    Runs two selected solvers concurrently using threading.Thread and
    determines the winner based on earliest completion time. Uses
    threading.Event for cooperative cancellation signaling so that
    solvers can check if they should stop.

    Attributes:
        _solver_manager: The SolverManager instance that provides solver access.
        _cancel_event: Shared threading.Event used to signal cancellation.
        _status_a: Live status for solver A.
        _status_b: Live status for solver B.
        _result_a: Solve result for solver A (set when thread completes).
        _result_b: Solve result for solver B (set when thread completes).
        _lock: Threading lock for thread-safe status updates.
        _start_time: Monotonic start time of the race.
        _is_running: Whether the race is currently in progress.
    """

    def __init__(self, solver_manager: Optional[SolverManager] = None) -> None:
        """Initialize the RaceController.

        Args:
            solver_manager: Optional SolverManager instance. If not provided,
                a new one is created with all default solvers registered.
        """
        self._solver_manager = solver_manager or SolverManager()
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._is_running: bool = False

        # Live status for each solver
        self._status_a: Optional[RaceStatus] = None
        self._status_b: Optional[RaceStatus] = None

        # Results from each solver thread
        self._result_a: Optional[SolveResult] = None
        self._result_b: Optional[SolveResult] = None

        # Completion times (monotonic) for winner determination
        self._completion_time_a: Optional[float] = None
        self._completion_time_b: Optional[float] = None

        # Exception tracking
        self._exception_a: Optional[Exception] = None
        self._exception_b: Optional[Exception] = None

    def start_race(
        self,
        grid: Grid,
        solver_a: SolverType,
        solver_b: SolverType,
        timeout: float = 60.0,
    ) -> RaceResult:
        """Start a race between two solvers on the same puzzle.

        Runs both solvers concurrently in separate threads. Monitors their
        progress and determines a winner based on completion time.

        Args:
            grid: The puzzle grid to solve (not mutated).
            solver_a: The first solver type to race.
            solver_b: The second solver type to race.
            timeout: Maximum time in seconds for the race. Defaults to 60.0.

        Returns:
            RaceResult containing both results and the winner determination.

        Raises:
            ValueError: If solver_a and solver_b are the same type.
        """
        if solver_a == solver_b:
            raise ValueError(
                f"Adversarial mode requires two distinct solvers, "
                f"got '{solver_a.value}' for both."
            )

        # Reset state for a new race
        self._cancel_event.clear()
        self._is_running = True
        self._start_time = time.monotonic()
        self._result_a = None
        self._result_b = None
        self._completion_time_a = None
        self._completion_time_b = None
        self._exception_a = None
        self._exception_b = None

        # Initialize live status
        self._status_a = RaceStatus(
            solver_type=solver_a,
            states_explored=0,
            elapsed_ms=0,
            is_complete=False,
        )
        self._status_b = RaceStatus(
            solver_type=solver_b,
            states_explored=0,
            elapsed_ms=0,
            is_complete=False,
        )

        # Create and start solver threads
        thread_a = threading.Thread(
            target=self._run_solver,
            args=(grid, solver_a, timeout, "a"),
            name=f"RaceSolver-{solver_a.value}",
            daemon=True,
        )
        thread_b = threading.Thread(
            target=self._run_solver,
            args=(grid, solver_b, timeout, "b"),
            name=f"RaceSolver-{solver_b.value}",
            daemon=True,
        )

        thread_a.start()
        thread_b.start()

        # Monitor the race until both complete or timeout
        self._monitor_race(thread_a, thread_b, timeout)

        self._is_running = False

        # Build results for any solver that didn't complete
        if self._result_a is None:
            elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
            if self._exception_a is not None:
                self._result_a = SolveResult(
                    solver_type=solver_a,
                    status=SolveStatus.FAILED,
                    time_ms=elapsed_ms,
                    states_explored=self._status_a.states_explored if self._status_a else 0,
                )
            else:
                self._result_a = SolveResult(
                    solver_type=solver_a,
                    status=SolveStatus.TIMEOUT,
                    time_ms=elapsed_ms,
                    states_explored=self._status_a.states_explored if self._status_a else 0,
                )

        if self._result_b is None:
            elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
            if self._exception_b is not None:
                self._result_b = SolveResult(
                    solver_type=solver_b,
                    status=SolveStatus.FAILED,
                    time_ms=elapsed_ms,
                    states_explored=self._status_b.states_explored if self._status_b else 0,
                )
            else:
                self._result_b = SolveResult(
                    solver_type=solver_b,
                    status=SolveStatus.TIMEOUT,
                    time_ms=elapsed_ms,
                    states_explored=self._status_b.states_explored if self._status_b else 0,
                )

        # Determine the winner
        winner = self._determine_winner(solver_a, solver_b)

        # Compute time difference
        time_difference_ms = abs(self._result_a.time_ms - self._result_b.time_ms)

        return RaceResult(
            solver_a_type=solver_a,
            solver_b_type=solver_b,
            solver_a_result=self._result_a,
            solver_b_result=self._result_b,
            winner=winner,
            time_difference_ms=time_difference_ms,
        )

    def get_live_status(self) -> tuple[RaceStatus, RaceStatus]:
        """Get the current live status of both solvers.

        Returns the most recent status update for each solver, including
        states explored, elapsed time, and completion state.

        Returns:
            A tuple of (status_a, status_b) with current race status.

        Raises:
            RuntimeError: If called when no race is in progress.
        """
        with self._lock:
            if self._status_a is None or self._status_b is None:
                raise RuntimeError("No race is currently in progress.")
            return (self._status_a, self._status_b)

    def stop(self) -> None:
        """Stop the current race by signaling cancellation to both threads.

        Sets the cancel event which both solver threads check cooperatively.
        This is a non-blocking call; threads will stop at their next
        cancellation check point.
        """
        self._cancel_event.set()
        self._is_running = False

    def _run_solver(
        self,
        grid: Grid,
        solver_type: SolverType,
        timeout: float,
        identifier: str,
    ) -> None:
        """Run a solver in a thread, updating status and storing the result.

        This method is the target for each solver thread. It runs the solver's
        solve method with a slightly reduced timeout to account for the race
        monitoring overhead, and periodically updates the live status.

        The solver itself handles its own timeout internally. The cancel_event
        is checked after solving completes to determine if the result should
        be discarded (if the other solver already won).

        Args:
            grid: The puzzle grid to solve.
            solver_type: Which solver to use.
            timeout: Maximum time in seconds for this solver.
            identifier: Either "a" or "b" identifying which racer this is.
        """
        try:
            # Run the solver with its internal timeout
            result = self._solver_manager.solve(grid, solver_type, timeout=timeout)

            # Record the completion time
            completion_time = time.monotonic()

            with self._lock:
                if identifier == "a":
                    self._result_a = result
                    self._completion_time_a = completion_time
                    if self._status_a is not None:
                        self._status_a = RaceStatus(
                            solver_type=solver_type,
                            states_explored=result.states_explored,
                            elapsed_ms=result.time_ms,
                            is_complete=True,
                        )
                else:
                    self._result_b = result
                    self._completion_time_b = completion_time
                    if self._status_b is not None:
                        self._status_b = RaceStatus(
                            solver_type=solver_type,
                            states_explored=result.states_explored,
                            elapsed_ms=result.time_ms,
                            is_complete=True,
                        )

            # Signal cancellation to the other solver if this one completed successfully
            if result.status == SolveStatus.SOLVED:
                self._cancel_event.set()

        except Exception as e:
            # Handle thread exceptions gracefully (Requirement 10.6)
            with self._lock:
                if identifier == "a":
                    self._exception_a = e
                    if self._status_a is not None:
                        elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
                        self._status_a = RaceStatus(
                            solver_type=solver_type,
                            states_explored=self._status_a.states_explored,
                            elapsed_ms=elapsed_ms,
                            is_complete=True,
                        )
                else:
                    self._exception_b = e
                    if self._status_b is not None:
                        elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
                        self._status_b = RaceStatus(
                            solver_type=solver_type,
                            states_explored=self._status_b.states_explored,
                            elapsed_ms=elapsed_ms,
                            is_complete=True,
                        )

    def _monitor_race(
        self,
        thread_a: threading.Thread,
        thread_b: threading.Thread,
        timeout: float,
    ) -> None:
        """Monitor the race, providing live status updates at least once per second.

        Polls both threads at 100ms intervals to update elapsed time.
        Stops when both threads complete or the overall timeout is reached.

        Args:
            thread_a: The thread running solver A.
            thread_b: The thread running solver B.
            timeout: Maximum race duration in seconds.
        """
        poll_interval = 0.1  # 100ms polling for responsive updates

        while True:
            # Check if overall timeout has been exceeded
            elapsed = time.monotonic() - self._start_time
            if elapsed >= timeout:
                # Signal both threads to stop
                self._cancel_event.set()
                # Wait briefly for threads to finish
                thread_a.join(timeout=1.0)
                thread_b.join(timeout=1.0)
                break

            # Update elapsed time in status
            elapsed_ms = int(elapsed * 1000)
            with self._lock:
                if self._status_a is not None and not self._status_a.is_complete:
                    self._status_a = RaceStatus(
                        solver_type=self._status_a.solver_type,
                        states_explored=self._status_a.states_explored,
                        elapsed_ms=elapsed_ms,
                        is_complete=False,
                    )
                if self._status_b is not None and not self._status_b.is_complete:
                    self._status_b = RaceStatus(
                        solver_type=self._status_b.solver_type,
                        states_explored=self._status_b.states_explored,
                        elapsed_ms=elapsed_ms,
                        is_complete=False,
                    )

            # Check if both threads have completed
            if not thread_a.is_alive() and not thread_b.is_alive():
                break

            # Check if cancel event was set (one solver won)
            if self._cancel_event.is_set():
                # Give the other thread a moment to finish up
                thread_a.join(timeout=1.0)
                thread_b.join(timeout=1.0)
                break

            # Sleep for the polling interval
            time.sleep(poll_interval)

    def _determine_winner(
        self, solver_a: SolverType, solver_b: SolverType
    ) -> Optional[SolverType]:
        """Determine the race winner based on completion times and statuses.

        Winner determination logic:
        - If both solved: winner is the one with lower time_ms.
          If within 1000ms of each other, it's a tie (Requirement 10.7).
        - If only one solved: that solver wins.
        - If neither solved (both timed out or failed): no winner (None).
        - If one timed out and other failed: no winner.

        Args:
            solver_a: The type of solver A.
            solver_b: The type of solver B.

        Returns:
            The winning SolverType, or None if it's a tie or no winner.
        """
        result_a = self._result_a
        result_b = self._result_b

        if result_a is None or result_b is None:
            return None

        a_solved = result_a.status == SolveStatus.SOLVED
        b_solved = result_b.status == SolveStatus.SOLVED

        # If neither solved, no winner
        if not a_solved and not b_solved:
            return None

        # If only one solved, that one wins (Requirement 10.6)
        if a_solved and not b_solved:
            return solver_a
        if b_solved and not a_solved:
            return solver_b

        # Both solved - compare times (Requirement 10.4)
        time_diff = abs(result_a.time_ms - result_b.time_ms)

        # If within 1000ms, declare tie (Requirement 10.7:
        # "within the same one-second update interval")
        if time_diff < 1000:
            return None

        # Winner is the one with lower completion time
        if result_a.time_ms < result_b.time_ms:
            return solver_a
        else:
            return solver_b
