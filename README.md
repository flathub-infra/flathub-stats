# Flathub Stats

Script to parse server logs into json files used for stats on flathub sites.

## Running via devcontainer

- Check out repo
- Start in vscode and let it start the container
- Run `poetry install`
- Generate some test data via `poetry run python generate-test-data.py`
- Run `poetry run python update-stats.py test/test-data.log`

## Test data

- The test data is not perfect, curretly, we're not creting correct fake data for delta downloads and updates
