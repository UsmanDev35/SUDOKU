# Requirements Document

## Introduction

This document specifies the requirements for an AI-powered Multi-Level Sudoku Solver and Evaluator system. The system generates Sudoku puzzles at multiple difficulty levels and solves them using four distinct AI search strategies: Backtracking Search (uninformed), Arc Consistency with MRV/Degree Heuristic (informed), Simulated Annealing (local search), and Constraint Propagation with Forward Checking. The system evaluates and compares algorithm performance across difficulty levels, presenting results through an interactive user interface.

This project fulfills the Complex Computing Problem (CCP) requirements for CSC202 Artificial Intelligence by demonstrating CSP formulation, multiple search paradigms, and empirical performance analysis.

## Glossary

- **Puzzle_Generator**: The module responsible for creating valid Sudoku puzzles at specified difficulty levels
- **Backtracking_Solver**: The uninformed search solver implementing depth-first backtracking without domain heuristics
- **Informed_Solver**: The informed search solver combining AC-3 algorithm with MRV and Degree Heuristic
- **Local_Search_Solver**: The local search solver implementing Simulated Annealing to reduce constraint violations
- **Constraint_Propagation_Solver**: The standalone solver using Forward Checking with constraint propagation
- **Performance_Evaluator**: The module that records and computes algorithm performance metrics
- **Dashboard**: The comparative analysis interface displaying performance metrics across algorithms and difficulty levels
- **User_Interface**: The CLI or GUI allowing user interaction with the system
- **Grid**: A 9x9 Sudoku board represented as an 81-cell structure divided into 9 rows, 9 columns, and 9 3x3 boxes
- **Cell**: A single position in the Grid that holds a value from 1-9 or is empty
- **Constraint**: A rule requiring all cells in a row, column, or box to contain distinct values
- **Domain**: The set of possible values (1-9) that a Cell can take given current constraints
- **State**: A snapshot of the Grid at a given point during the solving process
- **Backtrack**: The act of undoing a variable assignment and trying an alternative value
- **Arc_Consistency**: A constraint satisfaction condition where for every value in a variable's domain, there exists a consistent value in each neighboring variable's domain
- **MRV_Heuristic**: Minimum Remaining Values heuristic that selects the unassigned variable with the fewest legal values
- **Degree_Heuristic**: A tie-breaking heuristic that selects the variable involved in the most constraints with unassigned variables
- **Forward_Checking**: A technique that eliminates values from domains of unassigned variables that are inconsistent with the current assignment
- **Simulated_Annealing**: A probabilistic local search technique that accepts worse solutions with decreasing probability over time
- **Temperature**: The control parameter in Simulated_Annealing that determines the probability of accepting worse solutions
- **Cooling_Schedule**: The function that decreases Temperature over iterations in Simulated_Annealing
- **Difficulty_Level**: One of four categories (Easy, Medium, Hard, Expert) determined by the number of pre-filled cells and puzzle structure
- **Adversarial_Mode**: An optional competitive mode where two AI agents race to solve the same puzzle using different strategies

## Requirements

### Requirement 1: Puzzle Generation

**User Story:** As a user, I want to generate valid Sudoku puzzles at multiple difficulty levels, so that I can test and compare algorithm performance across varying complexity.

#### Acceptance Criteria

1. THE Puzzle_Generator SHALL produce 9x9 Sudoku puzzles where each row, each column, and each 3x3 box contains the digits 1 through 9 exactly once, with exactly one valid solution.
2. THE Puzzle_Generator SHALL support four Difficulty_Levels: Easy, Medium, Hard, and Expert.
3. WHEN the Difficulty_Level is Easy, THE Puzzle_Generator SHALL produce a Grid with 36 to 45 pre-filled cells.
4. WHEN the Difficulty_Level is Medium, THE Puzzle_Generator SHALL produce a Grid with 27 to 35 pre-filled cells.
5. WHEN the Difficulty_Level is Hard, THE Puzzle_Generator SHALL produce a Grid with 22 to 26 pre-filled cells.
6. WHEN the Difficulty_Level is Expert, THE Puzzle_Generator SHALL produce a Grid with 17 to 21 pre-filled cells.
7. THE Puzzle_Generator SHALL verify puzzle uniqueness by confirming exactly one valid solution exists before returning the puzzle to the caller.
8. WHEN a puzzle generation request is received, THE Puzzle_Generator SHALL return a valid puzzle within 30 seconds.
9. IF the Puzzle_Generator cannot produce a valid unique puzzle within 30 seconds, THEN THE Puzzle_Generator SHALL return an error indication specifying that generation failed due to timeout.

### Requirement 2: Backtracking Search Solver (Uninformed)

**User Story:** As a user, I want to solve Sudoku puzzles using a backtracking search algorithm, so that I can observe exhaustive state-space exploration without domain heuristics.

#### Acceptance Criteria

1. THE Backtracking_Solver SHALL implement depth-first search by selecting unassigned cells in a fixed order (left-to-right, top-to-bottom), skipping all pre-filled cells.
2. WHEN an unassigned Cell is selected, THE Backtracking_Solver SHALL try values 1 through 9 sequentially in ascending order.
3. WHEN a value assignment violates a Constraint, THE Backtracking_Solver SHALL perform a Backtrack and try the next value.
4. WHEN all values 1 through 9 for a Cell have been exhausted without finding a valid assignment, THE Backtracking_Solver SHALL Backtrack to the previous unassigned Cell in traversal order.
5. WHEN a complete valid assignment is found (all 81 cells filled with no Constraint violations), THE Backtracking_Solver SHALL return the solved Grid.
6. IF no valid assignment exists, THEN THE Backtracking_Solver SHALL return an unsolvable indication to the caller.
7. THE Backtracking_Solver SHALL record the number of States explored (incremented by one each time a value is assigned to a Cell) and the number of Backtracks performed (incremented by one each time an assignment is undone) during solving.
8. IF the input Grid contains pre-filled cells that violate a Constraint, THEN THE Backtracking_Solver SHALL return an unsolvable indication without attempting search.

### Requirement 3: Informed Search Solver (AC-3 + MRV + Degree Heuristic)

**User Story:** As a user, I want to solve Sudoku puzzles using an informed search strategy combining arc consistency and heuristics, so that I can observe intelligent search space pruning.

#### Acceptance Criteria

1. THE Informed_Solver SHALL implement the AC-3 algorithm to enforce Arc_Consistency across all constraint arcs (row, column, and box peers) before search begins and after each value assignment during search.
2. WHEN selecting the next variable to assign, THE Informed_Solver SHALL use the MRV_Heuristic to choose the unassigned Cell with the fewest remaining values in its Domain.
3. WHEN multiple cells share the same minimum Domain size, THE Informed_Solver SHALL apply the Degree_Heuristic as a tie-breaker by selecting the Cell involved in the most constraints with other unassigned Cells; if a tie persists, THE Informed_Solver SHALL select among tied Cells using a fixed deterministic order (left-to-right, top-to-bottom).
4. WHEN a value is assigned to a Cell, THE Informed_Solver SHALL propagate constraints by running AC-3 on all arcs involving the peers (same row, column, or box) of the assigned Cell.
5. IF Arc_Consistency reduces any Domain to empty, THEN THE Informed_Solver SHALL Backtrack to the previous assignment and restore all Domains to their state prior to that assignment.
6. WHEN a complete valid assignment is found, THE Informed_Solver SHALL return the solved Grid.
7. IF no valid assignment exists after exhausting all possibilities, THEN THE Informed_Solver SHALL report that the puzzle is unsolvable.
8. THE Informed_Solver SHALL record the number of States explored and Backtracks performed during solving.

### Requirement 4: Local Search Solver (Simulated Annealing)

**User Story:** As a user, I want to solve Sudoku puzzles using a local search approach, so that I can observe iterative improvement from a complete but possibly inconsistent assignment.

#### Acceptance Criteria

1. THE Local_Search_Solver SHALL initialize the Grid by filling each 3x3 box with a random permutation of values 1-9 while preserving pre-filled cells in their original positions.
2. THE Local_Search_Solver SHALL define a cost function that counts the total number of duplicate values across all rows and columns, where each extra occurrence of a value in a row or column counts as one violation.
3. WHEN selecting a neighbor State, THE Local_Search_Solver SHALL randomly choose one 3x3 box and swap two randomly selected non-fixed cells within that box.
4. WHEN the neighbor State has a cost less than or equal to the current State cost, THE Local_Search_Solver SHALL accept the neighbor State.
5. WHEN the neighbor State has a higher cost, THE Local_Search_Solver SHALL accept the neighbor State with probability e^(-delta/Temperature), where delta is the cost increase.
6. THE Local_Search_Solver SHALL decrease Temperature according to a geometric Cooling_Schedule (T_new = T_current × cooling_rate) with a configurable initial Temperature (default 1.0), a configurable cooling rate between 0.0 exclusive and 1.0 exclusive (default 0.99), and a configurable minimum Temperature threshold (default 0.001).
7. WHEN the cost reaches zero, THE Local_Search_Solver SHALL return the solved Grid.
8. IF the Temperature reaches the minimum threshold without finding a solution, THEN THE Local_Search_Solver SHALL restart with a new random initialization up to a configurable maximum number of restarts (default 10).
9. IF the maximum number of restarts is exhausted without finding a solution, THEN THE Local_Search_Solver SHALL report failure and return the best Grid found (lowest cost encountered across all restarts).
10. THE Local_Search_Solver SHALL record the number of States explored and the number of restarts performed during solving.

### Requirement 5: Constraint Propagation Solver (Forward Checking)

**User Story:** As a user, I want to solve Sudoku puzzles using constraint propagation with forward checking, so that I can observe how eliminating invalid candidates at each step reduces the search space.

#### Acceptance Criteria

1. THE Constraint_Propagation_Solver SHALL initialize the Domain of each empty Cell to values 1-9 and reduce each Domain by removing values already assigned to pre-filled cells in the same row, column, or box.
2. WHEN a value is assigned to a Cell, THE Constraint_Propagation_Solver SHALL remove that value from the Domains of all unassigned cells in the same row, column, and box (Forward_Checking).
3. IF Forward_Checking reduces any Domain to empty, THEN THE Constraint_Propagation_Solver SHALL Backtrack to the previous assignment and restore all Domains to their state immediately before that assignment.
4. WHEN a Cell's Domain is reduced to exactly one value, THE Constraint_Propagation_Solver SHALL assign that value to the Cell automatically (Naked Singles propagation) and apply Forward_Checking for the new assignment.
5. WHEN a value appears in exactly one Cell's Domain within a row, column, or box, THE Constraint_Propagation_Solver SHALL assign that value to that Cell (Hidden Singles propagation) and apply Forward_Checking for the new assignment.
6. WHEN selecting the next Cell to assign during search, THE Constraint_Propagation_Solver SHALL choose the unassigned Cell with the fewest remaining values in its Domain (MRV_Heuristic).
7. WHEN a complete valid assignment is found, THE Constraint_Propagation_Solver SHALL return the solved Grid.
8. IF all values in the Domain of the selected Cell lead to a dead end, THEN THE Constraint_Propagation_Solver SHALL report that the puzzle is unsolvable.
9. THE Constraint_Propagation_Solver SHALL record the number of States explored (each value assignment counts as one State) and Backtracks performed during solving.

### Requirement 6: Performance Evaluation

**User Story:** As a user, I want to see detailed performance metrics for each algorithm on each puzzle, so that I can compare their efficiency and understand their trade-offs.

#### Acceptance Criteria

1. THE Performance_Evaluator SHALL record the wall-clock time taken (in integer milliseconds) for each algorithm to solve a puzzle, measured from the start of the solving process to completion or timeout.
2. THE Performance_Evaluator SHALL record the number of States explored by each algorithm during solving.
3. THE Performance_Evaluator SHALL record the number of Backtracks performed by Backtracking_Solver, Informed_Solver, and Constraint_Propagation_Solver, and the number of restarts performed by Local_Search_Solver.
4. THE Performance_Evaluator SHALL rank algorithms by the number of States explored for the same puzzle, designating the algorithm with the fewest States explored as the most efficient for that puzzle.
5. WHEN an algorithm fails to solve a puzzle within a configurable timeout (default 60 seconds), THE Performance_Evaluator SHALL record the attempt as a timeout and capture the elapsed time, the number of States explored up to that point, and the number of Backtracks or restarts performed up to that point.
6. THE Performance_Evaluator SHALL compute mean, minimum, and maximum values for each metric across a minimum of 5 puzzles of the same Difficulty_Level for aggregate comparison.

### Requirement 7: Comparative Analysis Dashboard

**User Story:** As a user, I want to view a comparative analysis dashboard, so that I can visualise performance differences across all four algorithms at each difficulty level.

#### Acceptance Criteria

1. THE Dashboard SHALL display a comparison table showing time taken, States explored, Backtracks performed, and solution optimality for all four algorithms on a given puzzle.
2. THE Dashboard SHALL support displaying results grouped by Difficulty_Level.
3. THE Dashboard SHALL highlight the best-performing algorithm for each metric using visual emphasis (color or formatting), where "best-performing" is defined as the lowest value for time taken, States explored, and Backtracks performed.
4. WHEN multiple puzzles have been solved, THE Dashboard SHALL display aggregate statistics (mean, minimum, maximum) for each algorithm at each Difficulty_Level.
5. THE Dashboard SHALL provide a bar chart or formatted CLI table comparing algorithm performance visually.
6. THE Dashboard SHALL allow the user to export results to a CSV file for external analysis, including columns for puzzle ID, difficulty level, algorithm name, time taken, states explored, backtracks, and optimality rank.

### Requirement 8: User Interface

**User Story:** As a user, I want an interactive interface to control puzzle generation, algorithm selection, and result viewing, so that I can use the system effectively.

#### Acceptance Criteria

1. THE User_Interface SHALL provide a menu allowing the user to select a Difficulty_Level for puzzle generation from the four options: Easy, Medium, Hard, and Expert.
2. THE User_Interface SHALL provide a menu allowing the user to choose which algorithm to run (Backtracking_Solver, Informed_Solver, Local_Search_Solver, Constraint_Propagation_Solver, or all algorithms).
3. THE User_Interface SHALL display the initial unsolved Grid in a 9x9 layout with visible row, column, and 3x3 box separators, representing empty cells with a distinct placeholder character.
4. WHEN an algorithm completes solving, THE User_Interface SHALL display the solved Grid in the same 9x9 layout, visually distinguishing pre-filled cells from solver-assigned cells.
5. WHEN the user selects step-by-step mode, THE User_Interface SHALL display each State transition during the solving process with a configurable delay between steps (default 500 milliseconds, adjustable from 100 to 2000 milliseconds).
6. WHEN a solve operation completes, THE User_Interface SHALL display the time taken, number of States explored, and number of Backtracks performed for that operation.
7. THE User_Interface SHALL provide access to the comparative analysis Dashboard.
8. THE User_Interface SHALL provide navigation between all system features using numbered menu options or command inputs, displaying available options at each menu level.
9. IF the user enters an invalid menu selection or input, THEN THE User_Interface SHALL display an error message indicating the valid options and re-prompt the user without losing the current session state.

### Requirement 9: Step-by-Step Visualization

**User Story:** As a user, I want to observe the solving process step by step, so that I can understand how each algorithm explores the search space.

#### Acceptance Criteria

1. WHEN step-by-step mode is active, THE User_Interface SHALL display the current Grid State after each variable assignment or modification.
2. WHEN step-by-step mode is active for Backtracking_Solver, Informed_Solver, or Constraint_Propagation_Solver, THE User_Interface SHALL highlight the Cell being assigned by displaying it in a distinct color or marker.
3. WHEN step-by-step mode is active for Local_Search_Solver, THE User_Interface SHALL highlight both cells involved in the swap operation.
4. WHEN a Backtrack occurs in step-by-step mode, THE User_Interface SHALL indicate the Backtrack by displaying a "BACKTRACK" label and reverting the highlighted Cell to its previous state.
5. THE User_Interface SHALL allow the user to pause, resume, or skip to completion during step-by-step visualization.
6. THE User_Interface SHALL display a running count of States explored and Backtracks during step-by-step mode, updated after each step.

### Requirement 10: Adversarial Mode (Optional/Advanced)

**User Story:** As a user, I want to watch two AI agents race to solve the same puzzle using different strategies, so that I can directly compare algorithm speed in real-time.

#### Acceptance Criteria

1. THE User_Interface SHALL allow the user to select exactly two distinct algorithms from the four available solvers (Backtracking_Solver, Informed_Solver, Local_Search_Solver, Constraint_Propagation_Solver) for Adversarial_Mode.
2. WHEN Adversarial_Mode is started, THE system SHALL run both selected algorithms on the same puzzle concurrently.
3. WHILE Adversarial_Mode is running, THE User_Interface SHALL display both solving processes side by side, showing for each algorithm the current number of States explored and the elapsed time, updated at least once per second.
4. WHEN one algorithm completes first, THE User_Interface SHALL declare that algorithm as the winner and display the time difference in milliseconds.
5. WHEN both algorithms have completed or timed out, THE User_Interface SHALL display final performance metrics (time taken, States explored, and Backtracks performed) for both algorithms.
6. IF one or both algorithms exceed the configured timeout (default 60 seconds) during Adversarial_Mode, THEN THE system SHALL stop the timed-out algorithm, declare the other algorithm as the winner, and display partial metrics for the timed-out algorithm.
7. IF both algorithms complete within the same one-second update interval, THEN THE User_Interface SHALL declare a tie and display final metrics for both algorithms.

### Requirement 11: Code Structure and Modularity

**User Story:** As a developer, I want the codebase to be modular and well-documented, so that each component can be understood, tested, and extended independently.

#### Acceptance Criteria

1. THE system SHALL separate puzzle generation, algorithm implementation, constraint handling, performance reporting, and user interface into independent Python modules with no circular import dependencies between them.
2. THE system SHALL define interfaces between modules using Python abstract base classes or protocols that specify method signatures, parameter types, and return types for all inter-module interactions.
3. THE system SHALL include docstrings for all public classes and functions describing purpose, parameters, and return values.
4. THE system SHALL include inline comments in algorithm implementation modules explaining the algorithmic strategy, heuristic choices, and constraint propagation steps.
5. THE system SHALL follow PEP 8 style guidelines for Python code formatting, verifiable by passing a linter check with zero errors.
6. THE system SHALL include a README file documenting project structure, installation instructions, and at least one usage example for each major feature (puzzle generation, solving, and performance comparison).
7. THE system SHALL structure each module so that it can be unit-tested in isolation by depending only on interfaces (abstract base classes or protocols) rather than concrete implementations of other modules.
