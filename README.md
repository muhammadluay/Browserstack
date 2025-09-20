# Browserstack

Python tests for UI (Selenium) and API endpoints, runnable locally with pytest or across platforms via BrowserStack SDK.

## Quickstart
1) Create a virtualenv and install dependencies
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r selenium-python/requirements.txt
```
2) Configure environment
```
cp .env.example .env
# Fill values: BROWSERSTACK_USERNAME, BROWSERSTACK_ACCESS_KEY
# Optional: BROWSERSTACK_PROJECT_NAME, BROWSERSTACK_BUILD_NAME
```
Load into your shell when needed:
```
set -a; source .env; set +a
```

## Running Tests
- All local tests (API + UI):
```
pytest -q tests selenium-python/tests selenium-python/tests_api
```
- Use markers (from `pytest.ini`):
```
pytest -q -m ui
pytest -q -m api
pytest -q -m unhappy
```

### Run on BrowserStack (SDK)
```
cp browserstack.yml.example browserstack.yml
scripts/run_sdk.sh              # wraps pytest with browserstack-sdk
scripts/run_sdk.sh selenium-python/tests_api  # run subset
```
Alternatively:
```
USE_BSTACK_SDK=1 browserstack-sdk pytest -q selenium-python/tests
```
`browserstack.yml` is git‑ignored; do not commit real credentials.

## Project Structure
- `tests/` — API-only tests.
- `selenium-python/` — UI and API tests (`tests/`, `tests_api/`, `conftest.py`, `requirements.txt`).
- `browserstack-tests/` — local/SDK examples and helpers.
- `scripts/` — utilities like `run_sdk.sh`.
- `tools/` — helper scripts (e.g., `crawl_site.py`).
- `helpful/` — how‑to docs and guides.
- Config: `.env.example`, `browserstack.yml.example`.

## Test Management (CSV Import)
- Starter CSVs: `test-cases.csv`, `test-cases2.csv`, `test-cases3.csv`.
- Guide: `helpful/test-management-import.md`.
- Flow: Test Management → Projects → Test Cases → Import → Upload CSV → Map → Preview → Import.

## Contributing
See `AGENTS.md` for coding style, test conventions, and PR guidelines.
