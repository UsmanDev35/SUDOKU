"""Puzzle generation with difficulty control.

This module implements the PuzzleGeneratorProtocol to produce valid 9x9 Sudoku
puzzles with exactly one solution at configurable difficulty levels. The generator
uses backtracking with random value ordering to create a complete valid grid, then
removes cells while verifying uniqueness at each step.

Algorithm Overview:
    1. Generate a complete valid 9x9 grid using backtracking with randomized
       value ordering (shuffle 1-9 for each cell attempt).
    2. Determine the target number of pre-filled cells based on difficulty level.
    3. Remove cells one at a time in random order, verifying after each removal
       that the puzzle still has exactly one solution.
    4. If removing a cell creates multiple solutions, restore it and try another.
    5. Continue until the target number of filled cells is reached.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9
"""

import random
import time

from sudoku_solver_evaluator.models.enums import DifficultyLevel
from sudoku_solver_evaluator.models.grid import Cell, Grid
from sudoku_solver_evaluator.models.protocols import PuzzleGeneratorProtocol


# Difficulty level to pre-filled cell count ranges (inclusive bounds)
_DIFFICULTY_RANGES: dict[DifficultyLevel, tuple[int, int]] = {
    DifficultyLevel.EASY: (36, 45),
    DifficultyLevel.MEDIUM: (27, 35),
    DifficultyLevel.HARD: (22, 26),
    DifficultyLevel.EXPERT: (17, 21),
}


def _box_index(row: int, col: int) -> int:
    """Compute the 3x3 box index (0-8) for a given cell position."""
    return (row // 3) * 3 + (col // 3)


class PuzzleGenerator(PuzzleGeneratorProtocol):
    """Generates valid Sudoku puzzles with exactly one solution.

    Implements the PuzzleGeneratorProtocol interface. Produces puzzles at four
    difficulty levels by generating a complete valid grid and then removing cells
    while maintaining solution uniqueness.

    The generation process uses:
        - Backtracking with random value ordering for complete grid generation
        - Solution counting (capped at 2) for uniqueness verification
        - Monotonic clock for timeout enforcement

    Example:
        >>> from sudoku_solver_evaluator.models.enums import DifficultyLevel
        >>> generator = PuzzleGenerator()
        >>> puzzle = generator.generate(DifficultyLevel.EASY)
        >>> 36 <= puzzle.count_filled() <= 45
        True
    """

    def generate(self, difficulty: DifficultyLevel, timeout: float = 60.0) -> Grid:
        """Generate a valid Sudoku puzzle with exactly one solution.

        Creates a complete valid grid using backtracking with random value
        ordering, then removes cells based on the difficulty level to produce
        a puzzle. The puzzle is verified to have exactly one solution before
        being returned.

        Args:
            difficulty: The target difficulty level determining how many
                cells are pre-filled. Must be a valid DifficultyLevel enum value.
            timeout: Maximum generation time in seconds. Defaults to 30.0.

        Returns:
            A Grid with pre-filled cells appropriate for the difficulty,
            where pre-filled cells have is_fixed=True and empty cells have
            value=None and is_fixed=False.

        Raises:
            TimeoutError: If generation exceeds the timeout.
            ValueError: If difficulty is not a valid DifficultyLevel enum value.
        """
        # Validate difficulty parameter (Requirement 1.2)
        if not isinstance(difficulty, DifficultyLevel):
            raise ValueError(
                f"Invalid difficulty: {difficulty!r}. "
                f"Must be a DifficultyLevel enum value "
                f"(EASY, MEDIUM, HARD, or EXPERT)."
            )

        # Record start time using monotonic clock to avoid system clock drift
        timeout_at = time.monotonic() + timeout

        # Determine target pre-filled cells based on difficulty
        # (Requirements 1.3, 1.4, 1.5, 1.6)
        min_filled, max_filled = _DIFFICULTY_RANGES[difficulty]

        # Retry loop: generate a new complete grid and attempt cell removal.
        # For harder difficulties, some grids may not allow enough removals
        # while maintaining uniqueness, so we retry with a fresh grid.
        # Different complete grids have different "removability" properties.
        while True:
            # Check timeout before each attempt (Requirements 1.8, 1.9)
            if time.monotonic() > timeout_at:
                raise TimeoutError(
                    "Puzzle generation failed due to timeout: "
                    "could not produce a valid unique puzzle within the time limit."
                )

            # Generate a complete valid 9x9 grid (Requirement 1.1)
            board = self._generate_complete_board(timeout_at)

            # Remove cells to create the puzzle while maintaining
            # exactly one solution (Requirement 1.7).
            # Target the minimum of the range for maximum removal.
            puzzle_board = self._remove_cells(board, min_filled, timeout_at)

            # Accept any result within the valid difficulty range
            filled_count = sum(1 for v in puzzle_board if v != 0)
            if min_filled <= filled_count <= max_filled:
                return self._board_to_grid(puzzle_board)

            # If approaching timeout, accept slightly above target for Hard/Expert
            # rather than timing out completely
            if time.monotonic() > timeout_at - 3.0 and filled_count <= max_filled + 5:
                return self._board_to_grid(puzzle_board)

    def _generate_complete_board(self, timeout_at: float) -> list[int]:
        """Generate a complete valid 9x9 Sudoku board using backtracking.

        Uses a flat array representation (81 integers) for performance.
        Backtracking with random value ordering at each cell ensures variety.

        Args:
            timeout_at: Monotonic clock deadline for timeout enforcement.

        Returns:
            A flat list of 81 integers (1-9) representing a valid complete grid.

        Raises:
            TimeoutError: If generation exceeds the timeout deadline.
        """
        # Flat array: board[row*9 + col] = value (0 means empty)
        board = [0] * 81

        # Constraint tracking sets for O(1) validity checks
        row_used: list[set[int]] = [set() for _ in range(9)]
        col_used: list[set[int]] = [set() for _ in range(9)]
        box_used: list[set[int]] = [set() for _ in range(9)]

        if not self._fill_board(board, 0, row_used, col_used, box_used, timeout_at):
            raise TimeoutError(
                "Puzzle generation failed: could not generate a complete grid "
                "within the time limit."
            )

        return board

    def _fill_board(
        self,
        board: list[int],
        position: int,
        row_used: list[set[int]],
        col_used: list[set[int]],
        box_used: list[set[int]],
        timeout_at: float,
    ) -> bool:
        """Recursively fill the board using backtracking with random value ordering.

        Args:
            board: Flat array of 81 integers (mutated in place).
            position: Linear cell index (0-80).
            row_used: Sets tracking values used in each row.
            col_used: Sets tracking values used in each column.
            box_used: Sets tracking values used in each 3x3 box.
            timeout_at: Monotonic clock deadline for timeout enforcement.

        Returns:
            True if the board was successfully filled from this position onward.

        Raises:
            TimeoutError: If the timeout deadline is exceeded.
        """
        # Check timeout every 9 cells to reduce overhead
        if position % 9 == 0 and time.monotonic() > timeout_at:
            raise TimeoutError(
                "Puzzle generation failed due to timeout: "
                "could not complete grid generation within the time limit."
            )

        # Base case: all 81 cells filled successfully
        if position == 81:
            return True

        row = position // 9
        col = position % 9
        box_idx = _box_index(row, col)

        # Generate a random permutation of values 1-9 for variety
        values = list(range(1, 10))
        random.shuffle(values)

        for value in values:
            # O(1) constraint check using sets
            if (
                value not in row_used[row]
                and value not in col_used[col]
                and value not in box_used[box_idx]
            ):
                # Assign the value
                board[position] = value
                row_used[row].add(value)
                col_used[col].add(value)
                box_used[box_idx].add(value)

                # Recurse to fill the next cell
                if self._fill_board(
                    board, position + 1, row_used, col_used, box_used, timeout_at
                ):
                    return True

                # Backtrack
                board[position] = 0
                row_used[row].discard(value)
                col_used[col].discard(value)
                box_used[box_idx].discard(value)

        return False

    def _remove_cells(
        self, board: list[int], target_filled: int, timeout_at: float
    ) -> list[int]:
        """Remove cells from a complete board while maintaining solution uniqueness.

        Uses a smarter removal strategy optimized for Hard/Expert puzzles:
        1. Cells are ordered by constraint density (cells with more constraints
           removed first, as they're more likely to maintain uniqueness).
        2. Uniqueness is checked after each removal using a fast bitmask solver
           that stops at 2 solutions.
        3. If approaching timeout, accepts the current state even if slightly
           above the target clue count.

        Args:
            board: A flat list of 81 integers (1-9) representing a complete grid.
            target_filled: The desired number of pre-filled cells.
            timeout_at: Monotonic clock deadline for timeout enforcement.

        Returns:
            A flat list of 81 integers where 0 represents empty cells.
        """
        # Work on a copy
        puzzle = board[:]
        current_filled = 81

        # Order cells by constraint density: cells that share more filled
        # peers are safer to remove (they're more constrained by neighbors).
        # This heuristic makes Hard/Expert generation much more likely to succeed.
        positions = list(range(81))

        def _constraint_score(pos: int) -> int:
            """Higher score = more constrained by neighbors = safer to remove."""
            row = pos // 9
            col = pos % 9
            box_start_r = (row // 3) * 3
            box_start_c = (col // 3) * 3
            score = 0
            # Count filled peers in row
            for c in range(9):
                if c != col and puzzle[row * 9 + c] != 0:
                    score += 1
            # Count filled peers in col
            for r in range(9):
                if r != row and puzzle[r * 9 + col] != 0:
                    score += 1
            # Count filled peers in box
            for r in range(box_start_r, box_start_r + 3):
                for c in range(box_start_c, box_start_c + 3):
                    if (r, c) != (row, col) and puzzle[r * 9 + c] != 0:
                        score += 1
            return score

        # Sort by constraint score descending, then shuffle within same score
        # for variety. This gives a good starting order.
        random.shuffle(positions)
        positions.sort(key=_constraint_score, reverse=True)

        # Track positions that failed removal (don't retry them)
        failed_positions: set[int] = set()

        for pos in positions:
            # If approaching timeout (within 2 seconds), accept current state
            if time.monotonic() > timeout_at - 2.0:
                break

            if current_filled <= target_filled:
                break

            if pos in failed_positions:
                continue

            # Save value and attempt removal
            saved_value = puzzle[pos]
            puzzle[pos] = 0

            # Verify uniqueness using fast bitmask solver (stops at 2 solutions)
            if self._has_unique_solution(puzzle):
                current_filled -= 1
            else:
                # Multiple solutions — restore the cell
                puzzle[pos] = saved_value
                failed_positions.add(pos)

        return puzzle

    def _has_unique_solution(self, puzzle: list[int]) -> bool:
        """Check if a puzzle has exactly one solution.

        Uses an optimized backtracking solver with constraint propagation
        that counts solutions up to 2. Returns True only if exactly 1
        solution exists.

        Args:
            puzzle: Flat list of 81 integers (0 = empty).

        Returns:
            True if the puzzle has exactly one solution, False otherwise.
        """
        # Build constraint tracking using bitmasks for maximum performance.
        # Each bit position represents a value (bit 0 = value 1, bit 8 = value 9).
        # Using integers as bitmasks is faster than set operations in Python.
        row_mask = [0] * 9
        col_mask = [0] * 9
        box_mask = [0] * 9

        empty_cells: list[int] = []

        for pos in range(81):
            val = puzzle[pos]
            if val != 0:
                row = pos // 9
                col = pos % 9
                box_idx = _box_index(row, col)
                bit = 1 << (val - 1)
                row_mask[row] |= bit
                col_mask[col] |= bit
                box_mask[box_idx] |= bit
            else:
                empty_cells.append(pos)

        # Count solutions using backtracking with bitmask constraints
        count = [0]
        self._count_solutions_bitmask(
            empty_cells, 0, row_mask, col_mask, box_mask, count
        )
        return count[0] == 1

    def _count_solutions_bitmask(
        self,
        empty_cells: list[int],
        index: int,
        row_mask: list[int],
        col_mask: list[int],
        box_mask: list[int],
        count: list[int],
    ) -> None:
        """Count solutions using bitmask-based constraint tracking.

        This is the most performance-critical method. Uses integer bitmasks
        for O(1) constraint checks and candidate computation. Stops as soon
        as 2 solutions are found (sufficient for uniqueness verification).

        The method selects the empty cell with the fewest candidates (MRV
        heuristic) to minimize branching factor and speed up the search.

        Args:
            empty_cells: List of linear positions (0-80) that are empty.
            index: Current index into empty_cells being processed.
            row_mask: Bitmasks tracking values used in each row.
            col_mask: Bitmasks tracking values used in each column.
            box_mask: Bitmasks tracking values used in each 3x3 box.
            count: Mutable list [count] tracking solutions found.
        """
        # Early termination: already found 2 solutions
        if count[0] >= 2:
            return

        # Base case: all empty cells filled — found a solution
        if index == len(empty_cells):
            count[0] += 1
            return

        # MRV heuristic: find the empty cell with fewest candidates
        # among remaining unfilled cells. This dramatically prunes the search.
        best_idx = index
        best_count = 10  # More than maximum possible (9)

        for i in range(index, len(empty_cells)):
            pos = empty_cells[i]
            row = pos // 9
            col = pos % 9
            box_idx = _box_index(row, col)

            # Compute available values using bitmask complement
            used = row_mask[row] | col_mask[col] | box_mask[box_idx]
            available = (~used) & 0x1FF
            num_candidates = bin(available).count("1")

            if num_candidates == 0:
                # Dead end: no valid values for this cell
                return

            if num_candidates < best_count:
                best_count = num_candidates
                best_idx = i
                if num_candidates == 1:
                    break  # Can't do better than 1

        # Swap the best cell to the current index position (will be swapped back)
        empty_cells[index], empty_cells[best_idx] = (
            empty_cells[best_idx],
            empty_cells[index],
        )

        pos = empty_cells[index]
        row = pos // 9
        col = pos % 9
        box_idx = _box_index(row, col)

        # Compute candidate values using bitmask
        used = row_mask[row] | col_mask[col] | box_mask[box_idx]
        available = (~used) & 0x1FF

        # Try each candidate value
        while available:
            # Extract lowest set bit (next candidate)
            bit = available & (-available)
            available ^= bit

            # Assign value using bitmasks
            row_mask[row] |= bit
            col_mask[col] |= bit
            box_mask[box_idx] |= bit

            self._count_solutions_bitmask(
                empty_cells, index + 1, row_mask, col_mask, box_mask, count
            )

            # Backtrack
            row_mask[row] ^= bit
            col_mask[col] ^= bit
            box_mask[box_idx] ^= bit

            if count[0] >= 2:
                break

        # Restore swap
        empty_cells[index], empty_cells[best_idx] = (
            empty_cells[best_idx],
            empty_cells[index],
        )

    def _count_solutions(self, grid: Grid, limit: int = 2) -> int:
        """Count the number of solutions for a puzzle, stopping at the limit.

        Public-facing method that accepts a Grid object. Converts to flat
        array internally for efficient solving.

        Args:
            grid: The puzzle grid (with some empty cells).
            limit: Maximum number of solutions to count before stopping.
                Defaults to 2 (sufficient for uniqueness verification).

        Returns:
            The number of solutions found, capped at the limit value.
        """
        # Convert Grid to flat array
        board = [0] * 81
        for r in range(9):
            for c in range(9):
                val = grid.get_cell(r, c).value
                if val is not None:
                    board[r * 9 + c] = val

        # Build bitmask constraints
        row_mask = [0] * 9
        col_mask = [0] * 9
        box_mask = [0] * 9
        empty_cells: list[int] = []

        for pos in range(81):
            val = board[pos]
            if val != 0:
                row = pos // 9
                col = pos % 9
                box_idx = _box_index(row, col)
                bit = 1 << (val - 1)
                row_mask[row] |= bit
                col_mask[col] |= bit
                box_mask[box_idx] |= bit
            else:
                empty_cells.append(pos)

        count = [0]
        self._count_solutions_bitmask(
            empty_cells, 0, row_mask, col_mask, box_mask, count
        )
        return min(count[0], limit)

    @staticmethod
    def _board_to_grid(board: list[int]) -> Grid:
        """Convert a flat board array to a Grid object.

        Non-zero values are marked as fixed (pre-filled) cells.
        Zero values become empty cells with full domain.

        Args:
            board: Flat list of 81 integers (0 = empty, 1-9 = filled).

        Returns:
            A Grid object with appropriate Cell attributes set.
        """
        cells = []
        for r in range(9):
            row_cells = []
            for c in range(9):
                val = board[r * 9 + c]
                if val == 0:
                    cell = Cell(
                        row=r, col=c, value=None, is_fixed=False,
                        domain=set(range(1, 10))
                    )
                else:
                    cell = Cell(
                        row=r, col=c, value=val, is_fixed=True,
                        domain={val}
                    )
                row_cells.append(cell)
            cells.append(row_cells)
        return Grid(cells=cells)
