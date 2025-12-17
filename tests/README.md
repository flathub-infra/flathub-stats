# Tests

This directory contains tests for the flathub-stats project.

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=. --cov-report=term-missing

# Run snapshot tests only
uv run pytest tests/test_snapshots.py -v
```

## Snapshot Tests

The snapshot tests use [syrupy](https://github.com/tophat/syrupy) to verify the output JSON structure and data remain consistent.

### How They Work

Each test:
1. Generates test data using `generate-test-data.py` with a **specific seed** for reproducibility
2. Runs `update-stats.py` on the generated data
3. Compares the output JSON against a stored snapshot

### Updating Snapshots

When you intentionally change the output format:

```bash
# Update all snapshots
uv run pytest tests/test_snapshots.py --snapshot-update

# Review the changes
git diff tests/__snapshots__/

# Commit if changes are expected
git add tests/__snapshots__/
git commit -m "Update snapshots for output format change"
```

### Reproducing Test Data

To manually reproduce the test data:

```bash
# Generate same data as seed 42 test
python generate-test-data.py --seed 42 --count 100

# Process it
python update-stats.py test/test-data.log --dest test-output
```
