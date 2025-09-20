# BrowserStack SDK Quickstart (Testathon Live)

## Goal
Run the existing Selenium + Pytest suite on BrowserStack using the SDK, targeting:

- URL: https://testathon.live/

## Prerequisites
- Python 3 and pip installed
- BrowserStack Automate credentials (username + access key)

## 1) Set credentials (do NOT commit)
- Option A — Shell for current session:
  - `export BROWSERSTACK_USERNAME=<your_username>`
  - `export BROWSERSTACK_ACCESS_KEY=<your_access_key>`
- Option B — `.env` file (git-ignored):
  - Copy `.env.example` to `.env` and fill `BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`.
  - Load into your shell (optional): `set -a; source .env; set +a`

## 2) Create venv and install deps
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r selenium-python/requirements.txt`
- `pip install browserstack-sdk`

## 3) Configure BrowserStack SDK
- A starter `browserstack.yml` is present at the repo root and reads credentials from env.
- Edit matrix under `platforms` as needed (desktop + mobile). For public URL testing, keep `browserstackLocal: false`.

## 4) Point tests at Testathon Live
- Set environment for the smoke test:
  - Add to `.env`: `TEST_URL=https://testathon.live/`
  - Optional: `ASSERT_TITLE_CONTAINS=<substring from the page title>`
    - If omitted, the test asserts that the title is non-empty.
- The smoke test is at `selenium-python/tests/test_smoke.py:1` and already reports pass/fail to BrowserStack.

## 5) Run the suite via SDK (parallel across matrix)
- Prefer letting the SDK create the driver and inject auth. Set `USE_BSTACK_SDK=1` for SDK runs:
  - `USE_BSTACK_SDK=1 browserstack-sdk pytest -q selenium-python/tests`
- Useful flags:
  - Stop after N failures: `--maxfail=5`
  - Run failed first: `--failed-first`
  - Retries (install plugin first): `pip install pytest-rerunfailures` then add `--reruns 3 --reruns-delay 2`

## 6) Review results
- Open BrowserStack Automate dashboard → Builds → your `buildName` from `browserstack.yml`.
- Each session has video, logs, and the status set by the test.

## Notes
- Keep credentials out of source control. Rotate access keys if shared accidentally.
- For internal/staging hosts, set `browserstackLocal: true` in `browserstack.yml`.
- For a deeper matrix or retries guidance, see `helpful/test-orchestration-vs-pytest.md:1`.

### Why `USE_BSTACK_SDK=1`?
- Our pytest fixture supports two modes:
  - SDK mode: `webdriver.Remote(options=...)` and the SDK sets hub URL + HTTP auth.
  - Manual mode: we pass a Basic-auth URL ourselves.
- When the SDK wraps Selenium while we also pass a Basic-auth URL, it may rewrite the hub to a regional endpoint and drop credentials, causing `Authorization Required (401)` during session creation. Setting `USE_BSTACK_SDK=1` avoids that by letting the SDK handle everything.
