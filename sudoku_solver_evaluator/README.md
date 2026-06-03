# AI-Powered Multi-Level Sudoku Solver and Evaluator

A Python CLI application that generates Sudoku puzzles at four difficulty levels and solves them using four distinct AI search strategies. Designed for the CSC202 Artificial Intelligence course to demonstrate CSP formulation, multiple search paradigms, and empirical performance analysis.

## Features

- **Puzzle Generation**: Generate valid Sudoku puzzles at Easy, Medium, Hard, and Expert difficulty levels, each with exactly one solution.
- **Four Solving Algorithms**:
  - Backtracking Search (uninformed depth-first)
  - Informed Search (AC-3 + MRV + Degree Heuristic)
  - Simulated Annealing (local search)
  - Constraint Propagation with Forward Checking
- **Performance Evaluation**: Compare algorithm efficiency with metrics like time, states explored, and backtracks.
- **Step-by-Step Visualization**: Watch algorithms solve puzzles in real-time with Rich-based terminal UI.
- **Adversarial Mode**: Race two solvers against each other on the same puzzle.
- **CSV Export**: Export performance results for external analysis.

## Project Structure

```
sudoku_solver_evaluator/
├── main.py                     # Entry point
├── models/                     # Data models, enums, protocols
├── constraints/                # Constraint validation utilities
├── generator/                  # Puzzle generation with difficulty control
├── solvers/                    # Four solver implementations
├── evaluator/                  # Performance recording and CSV export
├── adversarial/                # Adversarial race mode
├── ui/                         # Rich CLI interface and visualization
├── tests/                      # Unit and property-based tests
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Installation

1. Ensure you have Python 3.10 or later installed.

2. Clone or download this project.

3. Install dependencies:

```bash
pip install -r sudoku_solver_evaluator/requirements.txt
```

## Usage

### Running the Application

```bash
python -m sudoku_solver_evaluator.main
```

### Generating a Puzzle

From the main menu, select "Generate Puzzle" and choose a difficulty level (Easy, Medium, Hard, or Expert). The system will generate a valid puzzle with exactly one solution.

### Solving a Puzzle

After generating a puzzle, select a solver algorithm or choose "All" to run all four algorithms. Results include the solved grid, time taken, states explored, and backtracks performed.

### Step-by-Step Visualization

Select "Step-by-Step Mode" to watch the solving process in real-time. You can adjust the delay between steps (100-2000ms) and pause/resume at any time.

### Comparing Performance

Use the "Dashboard" option to view a comparative table of all algorithms' performance on solved puzzles. The dashboard highlights the best-performing algorithm for each metric.

### Adversarial Mode

Select "Adversarial Mode" to race two algorithms against each other. Choose two different solvers and watch them compete in real-time.

### Exporting Results

Select "Export CSV" to save all performance data to a CSV file for external analysis.

## Running Tests

```bash
# Run all tests
pytest sudoku_solver_evaluator/tests/ -v

# Run with coverage report
pytest sudoku_solver_evaluator/tests/ --cov=sudoku_solver_evaluator --cov-report=html

# Run only property-based tests
pytest sudoku_solver_evaluator/tests/test_properties.py -v
```

## Dependencies

- **rich**: Terminal formatting and UI components
- **hypothesis**: Property-based testing framework
- **pytest**: Test runner
- **pytest-cov**: Coverage reporting for pytest
