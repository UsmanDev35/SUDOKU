# Implementation Plan: AI-Powered Multi-Level Sudoku Solver and Evaluator

## Overview

This plan builds the system incrementally: foundational models and constraints first, then puzzle generation, followed by each solver implementation, performance evaluation, CLI interface, and finally the adversarial mode. Each task is independently testable and builds on previous steps.

## Tasks

- [x] 1. Set up project structure and core models
  - [x] 1.1 Create project directory structure and configuration files
    - Create `sudoku_solver_evaluator/` package with all subpackages (`models/`, `constraints/`, `generator/`, `solvers/`, `evaluator/`, `adversarial/`, `ui/`, `tests/`)
    - Create `requirements.txt` with dependencies: `rich`, `hypothesis`, `pytest`, `pytest-cov`
    - Create `README.md` with project overview, installation instructions, and usage examples
    - Create all `__init__.py` files for proper package imports
    - _Requirements: 11.1, 11.6_

  - [x] 1.2 Implement enumerations and data models
    - Create `models/enums.py` with `DifficultyLevel`, `SolverType`, `SolveStatus`, `StepType` enums
    - Create `models/metrics.py` with `SolveResult`, `StepEvent`, `ComparisonTable`, `AggregateStats`, `AlgorithmStats`, `RaceResult`, `RaceStatus` dataclasses
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 1.3 Implement Grid and Cell data models
    - Create `models/grid.py` with `Cell` dataclass (row, col, value, is_fixed, domain, box property)
    - Implement `Grid` dataclass with all methods: `get_cell`, `set_value`, `clear_value`, `get_row`, `get_col`, `get_box`, `get_peers`, `get_empty_cells`, `is_complete`, `is_valid`, `copy`, `count_filled`, `from_2d_list`, `to_2d_list`
    - _Requirements: 1.1, 11.3_

  - [x] 1.4 Implement protocols and abstract interfaces
    - Create `models/protocols.py` with `SolverProtocol`, `PuzzleGeneratorProtocol`, `PerformanceEvaluatorProtocol` abstract base classes
    - Define method signatures with type annotations and docstrings
    - _Requirements: 11.2, 11.7_

  - [x] 1.5 Write unit tests for Grid and Cell models
    - Test Cell creation, box property calculation
    - Test Grid construction from 2D list, get_row/col/box/peers, is_valid, is_complete, copy
    - Test edge cases: empty grid, fully filled grid, single empty cell
    - _Requirements: 1.1_

- [x] 2. Implement constraint validation
  - [x] 2.1 Create constraint validation utilities
    - Create `constraints/validator.py` with functions: `is_valid_assignment`, `has_row_conflict`, `has_col_conflict`, `has_box_conflict`, `get_conflicts`, `is_grid_valid`
    - Validate that no row, column, or box contains duplicate non-zero values
    - Include docstrings and inline comments explaining constraint logic
    - _Requirements: 1.1, 2.3, 11.3, 11.4_

  - [x] 2.2 Write unit tests for constraint validation
    - Test valid and invalid assignments
    - Test conflict detection in rows, columns, and boxes
    - Test full grid validation with known valid and invalid grids
    - _Requirements: 1.1, 2.8_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement puzzle generator
  - [x] 4.1 Implement puzzle generation with difficulty control
    - Create `generator/puzzle_generator.py` implementing `PuzzleGeneratorProtocol`
    - Generate a complete valid grid using backtracking with random value ordering
    - Remove cells based on difficulty level ranges: Easy [36,45], Medium [27,35], Hard [22,26], Expert [17,21]
    - Verify puzzle uniqueness (exactly one solution) before returning
    - Implement 30-second timeout with `TimeoutError` on expiry
    - Validate difficulty parameter, raise `ValueError` for invalid input
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 4.2 Write property test for puzzle validity
    - **Property 1: Generated puzzles are valid Sudoku with unique solution**
    - **Validates: Requirements 1.1, 1.7**

  - [x] 4.3 Write property test for difficulty cell count ranges
    - **Property 2: Difficulty level determines pre-filled cell count**
    - **Validates: Requirements 1.3, 1.4, 1.5, 1.6**

- [x] 5. Implement Backtracking Solver
  - [x] 5.1 Implement Backtracking Search solver
    - Create `solvers/backtracking.py` implementing `SolverProtocol`
    - Implement depth-first search with fixed left-to-right, top-to-bottom cell ordering
    - Try values 1-9 sequentially in ascending order for each cell
    - Check constraints after each assignment; backtrack on violation
    - Emit `StepEvent` for each assignment (ASSIGN) and backtrack (BACKTRACK)
    - Record `states_explored` and `backtracks` metrics
    - Detect invalid initial grids and return UNSOLVABLE immediately
    - Implement configurable timeout (default 60s)
    - Work on a copy of the input grid (never mutate original)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [x] 5.2 Write property test for backtracking traversal order
    - **Property 5: Backtracking solver follows deterministic traversal and value ordering**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 5.3 Write property test for solver producing valid solutions
    - **Property 3: All solvers produce valid complete grids for solvable puzzles**
    - **Validates: Requirements 2.5**

  - [x] 5.4 Write property test for metrics consistency
    - **Property 6: Solver metrics are consistent with step events**
    - **Validates: Requirements 2.7**

- [x] 6. Implement Informed Solver (AC-3 + MRV + Degree)
  - [x] 6.1 Implement AC-3 algorithm and Informed Solver
    - Create `solvers/informed.py` implementing `SolverProtocol`
    - Implement AC-3 arc consistency enforcement on all constraint arcs
    - Implement MRV heuristic for variable selection (smallest domain)
    - Implement Degree Heuristic as tie-breaker, then positional order
    - Run AC-3 before search and after each assignment on affected arcs
    - Backtrack and restore domains when any domain becomes empty
    - Emit `StepEvent` for assignments, backtracks, and propagation
    - Record `states_explored` and `backtracks` metrics
    - Implement configurable timeout
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 6.2 Write property test for MRV selection
    - **Property 7: MRV-using solvers select minimum domain cell**
    - **Validates: Requirements 3.2**

  - [x] 6.3 Write property test for unsolvable detection
    - **Property 4: Solvers correctly identify unsolvable puzzles**
    - **Validates: Requirements 2.6, 2.8, 3.7**

- [x] 7. Implement Simulated Annealing Solver
  - [x] 7.1 Implement Simulated Annealing solver
    - Create `solvers/simulated_annealing.py` implementing `SolverProtocol`
    - Initialize each 3x3 box with random permutation of 1-9 preserving fixed cells
    - Implement cost function counting row + column duplicate values
    - Select neighbor by swapping two non-fixed cells within a random box
    - Accept better or equal moves; accept worse moves with probability e^(-delta/T)
    - Implement geometric cooling: T_new = T × cooling_rate (defaults: T=1.0, rate=0.99, min=0.001)
    - Restart with new initialization when temperature reaches threshold (max 10 restarts)
    - Return best grid found if max restarts exhausted (FAILED status)
    - Emit `StepEvent` with SWAP type for each swap operation
    - Record `states_explored`, `restarts`, and `best_cost` metrics
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

  - [x] 7.2 Write property test for SA initialization
    - **Property 8: SA initialization preserves fixed cells and fills boxes correctly**
    - **Validates: Requirements 4.1**

  - [x] 7.3 Write property test for SA cost function
    - **Property 9: SA cost function correctly counts row and column duplicates**
    - **Validates: Requirements 4.2**

  - [x] 7.4 Write property test for SA swap validity
    - **Property 10: SA swaps only non-fixed cells within the same box**
    - **Validates: Requirements 4.3**

  - [x] 7.5 Write property test for SA cooling schedule
    - **Property 11: SA temperature follows geometric cooling schedule**
    - **Validates: Requirements 4.6**

- [x] 8. Implement Forward Checking Solver
  - [x] 8.1 Implement Constraint Propagation with Forward Checking solver
    - Create `solvers/forward_checking.py` implementing `SolverProtocol`
    - Initialize domains for empty cells, reduce by existing assignments in peers
    - Implement Forward Checking: remove assigned value from all peer domains
    - Implement Naked Singles propagation (domain reduced to 1 value → auto-assign)
    - Implement Hidden Singles propagation (value in exactly one cell's domain in a unit → assign)
    - Use MRV heuristic for variable selection
    - Backtrack and restore domains on empty domain detection
    - Emit `StepEvent` for assignments, backtracks, and propagation
    - Record `states_explored` and `backtracks` metrics
    - Implement configurable timeout
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [x] 8.2 Write property test for FC domain initialization
    - **Property 12: FC domain initialization removes peer values**
    - **Validates: Requirements 5.1**

  - [x] 8.3 Write property test for FC forward checking
    - **Property 13: FC forward checking removes assigned value from peer domains**
    - **Validates: Requirements 5.2**

  - [x] 8.4 Write property test for FC propagation
    - **Property 14: FC propagation assigns forced values**
    - **Validates: Requirements 5.4, 5.5**

- [x] 9. Checkpoint - Ensure all solvers pass tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Solver Manager
  - [x] 10.1 Implement Solver Manager facade
    - Create `solvers/__init__.py` with `SolverManager` class
    - Implement `register`, `solve`, `solve_all`, `solve_stepwise` methods
    - Register all four solver implementations on initialization
    - Route solve requests to appropriate solver by `SolverType`
    - _Requirements: 8.2, 11.1_

- [x] 11. Implement Performance Evaluator and CSV Export
  - [x] 11.1 Implement performance recording and statistics
    - Create `evaluator/performance.py` implementing `PerformanceEvaluatorProtocol`
    - Record `SolveResult` entries keyed by puzzle_id and difficulty
    - Compute rankings by states_explored (ascending) for same puzzle
    - Compute aggregate stats (mean, min, max) across puzzles of same difficulty (minimum 5)
    - Handle timeout results by recording partial metrics
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 11.2 Implement CSV exporter
    - Create `evaluator/exporter.py` with CSV export functionality
    - Export columns: puzzle_id, difficulty_level, algorithm_name, time_taken, states_explored, backtracks, optimality_rank
    - Handle file write errors gracefully with descriptive messages
    - _Requirements: 7.6_

  - [x] 11.3 Write property test for evaluator statistics
    - **Property 15: Performance evaluator computes correct statistics and rankings**
    - **Validates: Requirements 6.4, 6.6**

  - [x] 11.4 Write property test for CSV round-trip
    - **Property 16: CSV export round-trip preserves data**
    - **Validates: Requirements 7.6**

- [x] 12. Implement CLI User Interface
  - [x] 12.1 Implement grid display with Rich formatting
    - Create `ui/display.py` with Rich-based grid rendering
    - Display 9x9 grid with row, column, and 3x3 box separators
    - Use distinct placeholder for empty cells
    - Visually distinguish pre-filled cells from solver-assigned cells (color/style)
    - Highlight active cell during step-by-step mode
    - _Requirements: 8.3, 8.4, 9.1, 9.2, 9.3_

  - [x] 12.2 Implement step-by-step visualization controller
    - Create `ui/visualization.py` with step-by-step playback
    - Accept `StepEvent` generator from solver and display each state transition
    - Configurable delay between steps (default 500ms, range 100-2000ms)
    - Display BACKTRACK label on backtrack events
    - Highlight swap cells for SA solver
    - Show running count of states explored and backtracks
    - Support pause, resume, and skip-to-completion controls
    - _Requirements: 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 12.3 Implement comparative analysis dashboard
    - Create `ui/dashboard.py` with Rich tables for comparison
    - Display comparison table: time, states, backtracks, optimality for all algorithms on a puzzle
    - Group results by difficulty level
    - Highlight best-performing algorithm per metric (lowest value)
    - Display aggregate statistics (mean, min, max) when multiple puzzles solved
    - Provide bar chart or formatted table for visual comparison
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 12.4 Implement main CLI menu and navigation
    - Create `ui/cli.py` with main menu loop
    - Menu options: generate puzzle (select difficulty), choose solver (single or all), step-by-step mode, view dashboard, adversarial mode, export CSV, exit
    - Numbered menu options with clear prompts at each level
    - Invalid input handling: display error with valid options, re-prompt without state loss
    - Create `main.py` entry point that initializes all components and starts CLI
    - _Requirements: 8.1, 8.2, 8.6, 8.7, 8.8, 8.9_

- [x] 13. Checkpoint - Ensure UI and evaluator work end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement Adversarial Mode
  - [x] 14.1 Implement adversarial race controller with threading
    - Create `adversarial/race.py` with `RaceController` class
    - Run two selected solvers concurrently using `threading.Thread`
    - Use `threading.Event` for cooperative cancellation
    - Determine winner by earliest completion time
    - Handle timeouts: stop timed-out solver, declare other as winner
    - Handle both-timeout: stop both, declare no winner
    - Handle thread exceptions gracefully
    - Provide live status updates (states explored, elapsed time) at least once per second
    - Compute time difference for winner declaration
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 14.2 Write property test for race winner correctness
    - **Property 17: Race winner has lower completion time**
    - **Validates: Requirements 10.4**

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All solvers work on copies of the input grid — never mutate the original
- Use `hypothesis` library with `@settings(max_examples=100)` for property tests
- Use `pytest` as the test runner with `pytest-cov` for coverage

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5", "2.1"] },
    { "id": 3, "tasks": ["2.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "6.1", "7.1", "8.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "7.2", "7.3", "7.4", "7.5", "8.2", "8.3", "8.4"] },
    { "id": 7, "tasks": ["10.1"] },
    { "id": 8, "tasks": ["11.1", "11.2"] },
    { "id": 9, "tasks": ["11.3", "11.4", "12.1", "12.2", "12.3"] },
    { "id": 10, "tasks": ["12.4"] },
    { "id": 11, "tasks": ["14.1"] },
    { "id": 12, "tasks": ["14.2"] }
  ]
}
```
