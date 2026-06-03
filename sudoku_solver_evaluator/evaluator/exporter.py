"""CSV export functionality for the Sudoku Solver Evaluator.

Provides functions to export recorded performance results to CSV format
and read them back for round-trip validation.

Requirements: 7.6
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolverType
from sudoku_solver_evaluator.models.metrics import SolveResult


# Column names for the CSV export
CSV_COLUMNS = [
    "puzzle_id",
    "difficulty_level",
    "algorithm_name",
    "time_taken",
    "states_explored",
    "backtracks",
    "optimality_rank",
]


class ExportError(Exception):
    """Raised when a CSV export or import operation fails."""

    pass


@dataclass
class ExportRow:
    """A single row of exported performance data.

    Attributes:
        puzzle_id: Unique identifier for the puzzle.
        difficulty_level: The difficulty level as a string.
        algorithm_name: The solver algorithm name.
        time_taken: Wall-clock time in milliseconds.
        states_explored: Number of states explored.
        backtracks: Number of backtracks performed.
        optimality_rank: Rank by states_explored (1 = best).
    """

    puzzle_id: str
    difficulty_level: str
    algorithm_name: str
    time_taken: int
    states_explored: int
    backtracks: int
    optimality_rank: int


def compute_optimality_ranks(rows: list[ExportRow]) -> list[ExportRow]:
    """Compute optimality ranks for export rows grouped by puzzle_id.

    Rankings are computed per-puzzle based on states_explored (ascending).
    Ties receive the same rank (dense ranking with gaps).

    Args:
        rows: List of ExportRow objects with optimality_rank to be computed.

    Returns:
        New list of ExportRow objects with optimality_rank filled in.
    """
    if not rows:
        return []

    # Group rows by puzzle_id
    groups: dict[str, list[ExportRow]] = defaultdict(list)
    for row in rows:
        groups[row.puzzle_id].append(row)

    result: list[ExportRow] = []

    for puzzle_id, group in groups.items():
        # Sort by states_explored ascending
        sorted_group = sorted(group, key=lambda r: r.states_explored)

        # Assign ranks with ties getting same rank
        ranked_group: list[ExportRow] = []
        current_rank = 1
        for i, row in enumerate(sorted_group):
            if i > 0 and row.states_explored > sorted_group[i - 1].states_explored:
                current_rank = i + 1
            ranked_group.append(
                ExportRow(
                    puzzle_id=row.puzzle_id,
                    difficulty_level=row.difficulty_level,
                    algorithm_name=row.algorithm_name,
                    time_taken=row.time_taken,
                    states_explored=row.states_explored,
                    backtracks=row.backtracks,
                    optimality_rank=current_rank,
                )
            )
        result.extend(ranked_group)

    return result


def export_csv(filepath: str, rows: list[ExportRow]) -> None:
    """Export performance data rows to a CSV file.

    Writes a CSV with columns: puzzle_id, difficulty_level, algorithm_name,
    time_taken, states_explored, backtracks, optimality_rank.

    Args:
        filepath: The file path where the CSV will be written.
        rows: List of ExportRow objects to write.

    Raises:
        ExportError: If the file cannot be written.
    """
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            for row in rows:
                writer.writerow([
                    row.puzzle_id,
                    row.difficulty_level,
                    row.algorithm_name,
                    row.time_taken,
                    row.states_explored,
                    row.backtracks,
                    row.optimality_rank,
                ])
    except OSError as e:
        raise ExportError(f"Failed to write CSV to {filepath}: {e}") from e


def read_csv(filepath: str) -> list[ExportRow]:
    """Read a CSV file and return a list of ExportRow objects.

    Args:
        filepath: The file path of the CSV to read.

    Returns:
        List of ExportRow objects parsed from the CSV.

    Raises:
        ExportError: If the file cannot be read.
    """
    try:
        rows: list[ExportRow] = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for record in reader:
                rows.append(
                    ExportRow(
                        puzzle_id=record["puzzle_id"],
                        difficulty_level=record["difficulty_level"],
                        algorithm_name=record["algorithm_name"],
                        time_taken=int(record["time_taken"]),
                        states_explored=int(record["states_explored"]),
                        backtracks=int(record["backtracks"]),
                        optimality_rank=int(record["optimality_rank"]),
                    )
                )
        return rows
    except OSError as e:
        raise ExportError(f"Failed to read CSV from {filepath}: {e}") from e


def export_results_csv(
    results: dict[str, dict[SolverType, SolveResult]],
    difficulty_map: dict[str, DifficultyLevel],
    filepath: str,
) -> None:
    """Export all recorded results to a CSV file via PerformanceEvaluator.

    Converts internal result structures to ExportRow objects, computes
    optimality ranks, and writes to CSV.

    Args:
        results: Mapping of puzzle_id to {solver_type: SolveResult}.
        difficulty_map: Mapping of puzzle_id to DifficultyLevel.
        filepath: The file path where the CSV will be written.

    Raises:
        ExportError: If the file cannot be written.
    """
    rows: list[ExportRow] = []
    for puzzle_id, solver_results in results.items():
        difficulty = difficulty_map.get(puzzle_id, DifficultyLevel.EASY)
        for solver_type, result in solver_results.items():
            rows.append(
                ExportRow(
                    puzzle_id=puzzle_id,
                    difficulty_level=difficulty.value,
                    algorithm_name=solver_type.value,
                    time_taken=result.time_ms,
                    states_explored=result.states_explored,
                    backtracks=result.backtracks,
                    optimality_rank=0,  # Will be computed by compute_optimality_ranks
                )
            )

    ranked_rows = compute_optimality_ranks(rows)
    export_csv(filepath, ranked_rows)
