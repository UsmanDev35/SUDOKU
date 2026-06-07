import random
import time
from sudoku_solver_evaluator.models.enums import DifficultyLevel
from sudoku_solver_evaluator.models.grid import Cell, Grid
from sudoku_solver_evaluator.models.protocols import PuzzleGeneratorProtocol
_DIFFICULTY_RANGES: dict[DifficultyLevel, tuple[int, int]] = {DifficultyLevel.EASY: (36, 45), DifficultyLevel.MEDIUM: (27, 35), DifficultyLevel.HARD: (22, 26), DifficultyLevel.EXPERT: (17, 21)}

def _box_index(row: int, col: int) -> int:
    # Compute the 3x3 box index for the given (row, col) position.
    return row // 3 * 3 + col // 3

class PuzzleGenerator(PuzzleGeneratorProtocol):

    def generate(self, difficulty: DifficultyLevel, timeout: float=60.0) -> Grid:
        # Generate a puzzle Grid for the requested difficulty within an optional timeout.
        if not isinstance(difficulty, DifficultyLevel):
            raise ValueError(f'Invalid difficulty: {difficulty!r}. Must be a DifficultyLevel enum value (EASY, MEDIUM, HARD, or EXPERT).')
        timeout_at = time.monotonic() + timeout
        min_filled, max_filled = _DIFFICULTY_RANGES[difficulty]
        while True:
            if time.monotonic() > timeout_at:
                raise TimeoutError('Puzzle generation failed due to timeout: could not produce a valid unique puzzle within the time limit.')
            board = self._generate_complete_board(timeout_at)
            puzzle_board = self._remove_cells(board, min_filled, timeout_at)
            filled_count = sum((1 for v in puzzle_board if v != 0))
            if min_filled <= filled_count <= max_filled:
                return self._board_to_grid(puzzle_board)
            if time.monotonic() > timeout_at - 3.0 and filled_count <= max_filled + 5:
                return self._board_to_grid(puzzle_board)

    def _generate_complete_board(self, timeout_at: float) -> list[int]:
        # Produce a fully-filled valid Sudoku board within the time limit.
        board = [0] * 81
        row_used: list[set[int]] = [set() for _ in range(9)]
        col_used: list[set[int]] = [set() for _ in range(9)]
        box_used: list[set[int]] = [set() for _ in range(9)]
        if not self._fill_board(board, 0, row_used, col_used, box_used, timeout_at):
            raise TimeoutError('Puzzle generation failed: could not generate a complete grid within the time limit.')
        return board

    def _fill_board(self, board: list[int], position: int, row_used: list[set[int]], col_used: list[set[int]], box_used: list[set[int]], timeout_at: float) -> bool:
        # Recursively fill the board using backtracking to create a complete solution.
        if position % 9 == 0 and time.monotonic() > timeout_at:
            raise TimeoutError('Puzzle generation failed due to timeout: could not complete grid generation within the time limit.')
        if position == 81:
            return True
        row = position // 9
        col = position % 9
        box_idx = _box_index(row, col)
        values = list(range(1, 10))
        random.shuffle(values)
        for value in values:
            if value not in row_used[row] and value not in col_used[col] and (value not in box_used[box_idx]):
                board[position] = value
                row_used[row].add(value)
                col_used[col].add(value)
                box_used[box_idx].add(value)
                if self._fill_board(board, position + 1, row_used, col_used, box_used, timeout_at):
                    return True
                board[position] = 0
                row_used[row].discard(value)
                col_used[col].discard(value)
                box_used[box_idx].discard(value)
        return False

    def _remove_cells(self, board: list[int], target_filled: int, timeout_at: float) -> list[int]:
        # Remove cells from a full board to create a puzzle with approximately target_filled cells.
        puzzle = board[:]
        current_filled = 81
        positions = list(range(81))

        def _constraint_score(pos: int) -> int:
            # Heuristic score counting filled neighbors for prioritizing removals.
            row = pos // 9
            col = pos % 9
            box_start_r = row // 3 * 3
            box_start_c = col // 3 * 3
            score = 0
            for c in range(9):
                if c != col and puzzle[row * 9 + c] != 0:
                    score += 1
            for r in range(9):
                if r != row and puzzle[r * 9 + col] != 0:
                    score += 1
            for r in range(box_start_r, box_start_r + 3):
                for c in range(box_start_c, box_start_c + 3):
                    if (r, c) != (row, col) and puzzle[r * 9 + c] != 0:
                        score += 1
            return score
        random.shuffle(positions)
        positions.sort(key=_constraint_score, reverse=True)
        failed_positions: set[int] = set()
        for pos in positions:
            if time.monotonic() > timeout_at - 2.0:
                break
            if current_filled <= target_filled:
                break
            if pos in failed_positions:
                continue
            saved_value = puzzle[pos]
            puzzle[pos] = 0
            if self._has_unique_solution(puzzle):
                current_filled -= 1
            else:
                puzzle[pos] = saved_value
                failed_positions.add(pos)
        return puzzle

    def _has_unique_solution(self, puzzle: list[int]) -> bool:
        # Check whether the puzzle has exactly one valid solution.
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
                bit = 1 << val - 1
                row_mask[row] |= bit
                col_mask[col] |= bit
                box_mask[box_idx] |= bit
            else:
                empty_cells.append(pos)
        count = [0]
        self._count_solutions_bitmask(empty_cells, 0, row_mask, col_mask, box_mask, count)
        return count[0] == 1

    def _count_solutions_bitmask(self, empty_cells: list[int], index: int, row_mask: list[int], col_mask: list[int], box_mask: list[int], count: list[int]) -> None:
        # Count solutions using bitmask backtracking; stops after finding two or more.
        if count[0] >= 2:
            return
        if index == len(empty_cells):
            count[0] += 1
            return
        best_idx = index
        best_count = 10
        for i in range(index, len(empty_cells)):
            pos = empty_cells[i]
            row = pos // 9
            col = pos % 9
            box_idx = _box_index(row, col)
            used = row_mask[row] | col_mask[col] | box_mask[box_idx]
            available = ~used & 511
            num_candidates = bin(available).count('1')
            if num_candidates == 0:
                return
            if num_candidates < best_count:
                best_count = num_candidates
                best_idx = i
                if num_candidates == 1:
                    break
        empty_cells[index], empty_cells[best_idx] = (empty_cells[best_idx], empty_cells[index])
        pos = empty_cells[index]
        row = pos // 9
        col = pos % 9
        box_idx = _box_index(row, col)
        used = row_mask[row] | col_mask[col] | box_mask[box_idx]
        available = ~used & 511
        while available:
            bit = available & -available
            available ^= bit
            row_mask[row] |= bit
            col_mask[col] |= bit
            box_mask[box_idx] |= bit
            self._count_solutions_bitmask(empty_cells, index + 1, row_mask, col_mask, box_mask, count)
            row_mask[row] ^= bit
            col_mask[col] ^= bit
            box_mask[box_idx] ^= bit
            if count[0] >= 2:
                break
        empty_cells[index], empty_cells[best_idx] = (empty_cells[best_idx], empty_cells[index])

    def _count_solutions(self, grid: Grid, limit: int=2) -> int:
        # Count solutions for a given grid up to a specified limit (default 2).
        board = [0] * 81
        for r in range(9):
            for c in range(9):
                val = grid.get_cell(r, c).value
                if val is not None:
                    board[r * 9 + c] = val
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
                bit = 1 << val - 1
                row_mask[row] |= bit
                col_mask[col] |= bit
                box_mask[box_idx] |= bit
            else:
                empty_cells.append(pos)
        count = [0]
        self._count_solutions_bitmask(empty_cells, 0, row_mask, col_mask, box_mask, count)
        return min(count[0], limit)

    @staticmethod
    def _board_to_grid(board: list[int]) -> Grid:
        # Convert a flat board list into a `Grid` of `Cell` objects.
        cells = []
        for r in range(9):
            row_cells = []
            for c in range(9):
                val = board[r * 9 + c]
                if val == 0:
                    cell = Cell(row=r, col=c, value=None, is_fixed=False, domain=set(range(1, 10)))
                else:
                    cell = Cell(row=r, col=c, value=val, is_fixed=True, domain={val})
                row_cells.append(cell)
            cells.append(row_cells)
        return Grid(cells=cells)