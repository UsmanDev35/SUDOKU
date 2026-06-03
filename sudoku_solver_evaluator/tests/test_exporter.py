"""Unit tests for the CSV exporter module."""

import os
import tempfile

import pytest

from sudoku_solver_evaluator.evaluator.exporter import (
    CSV_COLUMNS,
    ExportError,
    ExportRow,
    compute_optimality_ranks,
    export_csv,
    read_csv,
)


@pytest.fixture
def sample_rows():
    """Create sample export rows for testing."""
    return [
        ExportRow(
            puzzle_id="puzzle_1",
            difficulty_level="easy",
            algorithm_name="backtracking",
            time_taken=150,
            states_explored=500,
            backtracks=30,
            optimality_rank=0,
        ),
        ExportRow(
            puzzle_id="puzzle_1",
            difficulty_level="easy",
            algorithm_name="informed",
            time_taken=80,
            states_explored=200,
            backtracks=10,
            optimality_rank=0,
        ),
        ExportRow(
            puzzle_id="puzzle_1",
            difficulty_level="easy",
            algorithm_name="forward_checking",
            time_taken=100,
            states_explored=300,
            backtracks=15,
            optimality_rank=0,
        ),
    ]


class TestExportCSV:
    """Tests for the export_csv function."""

    def test_export_creates_file_with_correct_columns(self, sample_rows):
        """Export should create a CSV file with the expected header columns."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp:
            filepath = tmp.name

        try:
            export_csv(filepath, sample_rows)
            with open(filepath, "r", encoding="utf-8") as f:
                header = f.readline().strip()
            assert header == ",".join(CSV_COLUMNS)
        finally:
            os.unlink(filepath)

    def test_export_writes_correct_number_of_rows(self, sample_rows):
        """Export should write one data row per ExportRow."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp:
            filepath = tmp.name

        try:
            export_csv(filepath, sample_rows)
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # 1 header + 3 data rows
            assert len(lines) == 4
        finally:
            os.unlink(filepath)

    def test_export_empty_rows(self):
        """Export with empty row list should produce a file with only a header."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp:
            filepath = tmp.name

        try:
            export_csv(filepath, [])
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1
            assert lines[0].strip() == ",".join(CSV_COLUMNS)
        finally:
            os.unlink(filepath)

    def test_export_handles_write_error_gracefully(self):
        """Export should raise ExportError with descriptive message on write failure."""
        # Use a path that doesn't exist to trigger an IOError
        bad_path = "/nonexistent_dir_xyz/impossible/output.csv"
        rows = [
            ExportRow(
                puzzle_id="p1",
                difficulty_level="easy",
                algorithm_name="backtracking",
                time_taken=100,
                states_explored=50,
                backtracks=5,
                optimality_rank=1,
            )
        ]
        with pytest.raises(ExportError) as exc_info:
            export_csv(bad_path, rows)
        assert bad_path in str(exc_info.value)
        assert "Failed to write CSV" in str(exc_info.value)


class TestReadCSV:
    """Tests for the read_csv function."""

    def test_round_trip_preserves_data(self, sample_rows):
        """Writing then reading a CSV should produce identical data."""
        # First compute ranks so the data is meaningful
        ranked_rows = compute_optimality_ranks(sample_rows)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp:
            filepath = tmp.name

        try:
            export_csv(filepath, ranked_rows)
            read_back = read_csv(filepath)
            assert len(read_back) == len(ranked_rows)
            for original, parsed in zip(ranked_rows, read_back):
                assert original.puzzle_id == parsed.puzzle_id
                assert original.difficulty_level == parsed.difficulty_level
                assert original.algorithm_name == parsed.algorithm_name
                assert original.time_taken == parsed.time_taken
                assert original.states_explored == parsed.states_explored
                assert original.backtracks == parsed.backtracks
                assert original.optimality_rank == parsed.optimality_rank
        finally:
            os.unlink(filepath)

    def test_read_handles_missing_file_gracefully(self):
        """Read should raise ExportError with descriptive message for missing file."""
        with pytest.raises(ExportError) as exc_info:
            read_csv("/nonexistent_file_xyz.csv")
        assert "Failed to read CSV" in str(exc_info.value)


class TestComputeOptimalityRanks:
    """Tests for the compute_optimality_ranks function."""

    def test_ranks_by_states_explored_ascending(self, sample_rows):
        """Rank 1 should go to the solver with fewest states_explored."""
        ranked = compute_optimality_ranks(sample_rows)
        # Sort ranked by optimality_rank to check ordering
        ranked_sorted = sorted(ranked, key=lambda r: r.optimality_rank)
        assert ranked_sorted[0].algorithm_name == "informed"  # 200 states
        assert ranked_sorted[0].optimality_rank == 1
        assert ranked_sorted[1].algorithm_name == "forward_checking"  # 300 states
        assert ranked_sorted[1].optimality_rank == 2
        assert ranked_sorted[2].algorithm_name == "backtracking"  # 500 states
        assert ranked_sorted[2].optimality_rank == 3

    def test_tied_states_explored_get_same_rank(self):
        """Solvers with the same states_explored should receive the same rank."""
        rows = [
            ExportRow("p1", "medium", "backtracking", 100, 300, 10, 0),
            ExportRow("p1", "medium", "informed", 80, 300, 5, 0),
            ExportRow("p1", "medium", "forward_checking", 90, 500, 8, 0),
        ]
        ranked = compute_optimality_ranks(rows)
        rank_map = {r.algorithm_name: r.optimality_rank for r in ranked}
        assert rank_map["backtracking"] == 1
        assert rank_map["informed"] == 1
        assert rank_map["forward_checking"] == 3

    def test_multiple_puzzles_ranked_independently(self):
        """Each puzzle should be ranked independently."""
        rows = [
            ExportRow("p1", "easy", "backtracking", 100, 500, 10, 0),
            ExportRow("p1", "easy", "informed", 80, 200, 5, 0),
            ExportRow("p2", "hard", "backtracking", 200, 100, 20, 0),
            ExportRow("p2", "hard", "informed", 150, 400, 15, 0),
        ]
        ranked = compute_optimality_ranks(rows)
        # For p1: informed (200) < backtracking (500)
        p1_rows = {r.algorithm_name: r for r in ranked if r.puzzle_id == "p1"}
        assert p1_rows["informed"].optimality_rank == 1
        assert p1_rows["backtracking"].optimality_rank == 2
        # For p2: backtracking (100) < informed (400)
        p2_rows = {r.algorithm_name: r for r in ranked if r.puzzle_id == "p2"}
        assert p2_rows["backtracking"].optimality_rank == 1
        assert p2_rows["informed"].optimality_rank == 2

    def test_empty_input_returns_empty(self):
        """Empty input should produce empty output."""
        assert compute_optimality_ranks([]) == []
