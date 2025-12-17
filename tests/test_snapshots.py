#!/usr/bin/env python3
"""Snapshot tests for flathub-stats with reproducible seeds"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from syrupy.extensions.amber import AmberSnapshotExtension


class SeparateFileExtension(AmberSnapshotExtension):
    """Extension that creates a separate file for each test"""

    @classmethod
    def dirname(cls, *, test_location):
        # Return a path that includes the test name
        return (
            Path(test_location.filepath).parent
            / "__snapshots__"
            / test_location.testname
        )


@pytest.fixture
def snapshot(snapshot):
    """Override snapshot fixture to use separate files"""
    return snapshot.use_extension(SeparateFileExtension)


def test_stats_with_seed_42(snapshot, tmp_path):
    """Test stats generation with seed 42 - verifies complete output structure"""
    # Generate test data with a fixed seed for reproducibility
    result = subprocess.run(
        [sys.executable, "generate-test-data.py", "--seed", "42", "--count", "100"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to generate test data: {result.stderr}"

    # Move generated log to tmp_path
    source_log = Path(__file__).parent.parent / "test" / "test-data.log"
    test_log = tmp_path / "test-data.log"
    shutil.move(str(source_log), str(test_log))

    # Run update-stats.py
    stats_dir = tmp_path / "stats"
    result = subprocess.run(
        [
            sys.executable,
            "update-stats.py",
            str(test_log),
            "--dest",
            str(stats_dir),
            "--ref-cache",
            str(tmp_path / "ref-cache.json"),
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to process stats: {result.stderr}"

    # Verify the output file exists
    output_file = stats_dir / "2023" / "05" / "16.json"
    assert output_file.exists(), f"Output file not created at {output_file}"

    # Load and snapshot the JSON
    with open(output_file) as f:
        data = json.load(f)

    assert data == snapshot


def test_stats_with_seed_123(snapshot, tmp_path):
    """Test stats generation with seed 123 - different data, same structure"""
    # Generate test data with a different seed
    result = subprocess.run(
        [sys.executable, "generate-test-data.py", "--seed", "123", "--count", "50"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to generate test data: {result.stderr}"

    source_log = Path(__file__).parent.parent / "test" / "test-data.log"
    test_log = tmp_path / "test-data.log"
    shutil.move(str(source_log), str(test_log))

    stats_dir = tmp_path / "stats"
    result = subprocess.run(
        [
            sys.executable,
            "update-stats.py",
            str(test_log),
            "--dest",
            str(stats_dir),
            "--ref-cache",
            str(tmp_path / "ref-cache.json"),
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to process stats: {result.stderr}"

    output_file = stats_dir / "2023" / "05" / "16.json"
    with open(output_file) as f:
        data = json.load(f)

    assert data == snapshot


def test_stats_with_seed_999_small_dataset(snapshot, tmp_path):
    """Test with seed 999 and small dataset - ensures consistency with minimal data"""
    result = subprocess.run(
        [sys.executable, "generate-test-data.py", "--seed", "999", "--count", "10"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    source_log = Path(__file__).parent.parent / "test" / "test-data.log"
    test_log = tmp_path / "test-data.log"
    shutil.move(str(source_log), str(test_log))

    stats_dir = tmp_path / "stats"
    result = subprocess.run(
        [
            sys.executable,
            "update-stats.py",
            str(test_log),
            "--dest",
            str(stats_dir),
            "--ref-cache",
            str(tmp_path / "ref-cache.json"),
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    output_file = stats_dir / "2023" / "05" / "16.json"
    with open(output_file) as f:
        data = json.load(f)

    # Verify structure
    assert "date" in data
    assert "downloads" in data
    assert "refs" in data

    # Snapshot the complete output
    assert data == snapshot
