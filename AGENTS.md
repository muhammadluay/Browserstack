# Repository Guidelines

## Project Structure & Module Organization
- Root: `tests/` (API tests), `selenium-python/` (UI + API tests, `conftest.py`, `requirements.txt`), `browserstack-tests/` (local/SDK examples), `scripts/` (e.g., `run_sdk.sh`), `tools/` (utilities like `crawl_site.py`), `helpful/` (how‑to docs).
- Config: `.env.example` → copy to `.env`; `browserstack.yml.example` → copy to `browserstack.yml` (git‑ignored).
- Data: `test-cases*.csv` seed files.

## Build, Test, and Development Commands
- Create venv + install deps:
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install -r selenium-python/requirements.txt`
  - Optional: `pip install -r browserstack-tests/requirements.txt`
- Run all local tests:
  - `pytest -q tests selenium-python/tests selenium-python/tests_api`
- Run markers (from `pytest.ini`):
  - UI: `pytest -q -m ui`
  - API: `pytest -q -m api`
  - Unhappy paths: `pytest -q -m unhappy`
- Run via BrowserStack SDK (matrix from `browserstack.yml`):
  - `cp browserstack.yml.example browserstack.yml`
  - `scripts/run_sdk.sh` (loads `.env`, wraps `pytest` with `browserstack-sdk`).

## Coding Style & Naming Conventions
- Python (3.11+): PEP 8, 4‑space indents, `snake_case` files and functions.
- Tests: files start with `test_*.py`; keep tests small, deterministic, and independent.
- Use type hints where practical; prefer explicit waits in Selenium.
- Env/config keys are UPPER_SNAKE_CASE (e.g., `BROWSERSTACK_USERNAME`, `TEST_URL`).

## Testing Guidelines
- Framework: `pytest`; markers: `ui`, `api`, `unhappy`.
- Place UI tests in `selenium-python/tests/`; API tests in `tests/` or `selenium-python/tests_api/`.
- Configure credentials/URL via `.env` or `browserstack.yml`. Do not hardcode secrets.
- Provide clear assertions and skip/xfail with rationale when necessary.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits (`feat:`, `fix:`, `chore:`). Scope by area (e.g., `ui`, `api`).
- PRs must include: purpose, scope, test plan (`pytest` output), and BrowserStack session/build link when applicable.
- Link related issues, update docs (`README.md`, `helpful/*`) when behavior changes.

## Security & Configuration Tips
- Never commit `.env` or real credentials; keep `browserstack.yml` untracked.
- Prefer environment variables; use `.env.example` to document required keys.
