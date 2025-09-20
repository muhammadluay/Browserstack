# Test Orchestration (ITO) vs. Pytest Equivalents

## Summary
- The provided YAML keys (`testOrchestrationOptions` -> `retryTestsOnFailure`, `abortBuildOnFailure`, `runSmartSelection`, etc.) belong to BrowserStack Intelligent Test Orchestration (ITO). They are not recognized by the simple BrowserStack SDK `browserstack.yml` used in this repo, so adding them here will be ignored unless your account and setup use ITO-specific config.
- You can achieve similar behavior immediately with pytest flags/plugins while still running on BrowserStack via the SDK.

## What to use now (works in this repo)
- Retries on failure: add `pytest-rerunfailures` to your environment, then run with `--reruns 5 --reruns-delay 2`.
- Abort build after N failures: `--maxfail=5` (or `-x` to stop on first failure).
- Run failed first / only previously failed: `--failed-first` or `--last-failed`.
- Skip/handle flaky tests: mark them (e.g., `@pytest.mark.flaky(reruns=3, reruns_delay=1)`) or use `--reruns` globally.
- Change-based selection ("smart selection"): not in this SDK YAML. Consider `pytest-testmon` locally/CI, or enable BrowserStack ITO if available on your account.

## Example commands
- With SDK matrix (recommended):
  - `browserstack-sdk pytest -q selenium-python/tests --reruns 5 --reruns-delay 2 --maxfail=5 --failed-first`
  - Only previously failed tests: `browserstack-sdk pytest -q --last-failed --reruns 2`
- Without SDK (single remote capability defined in code):
  - `pytest -q selenium-python/tests --reruns 5 --maxfail=5`

## Minimal setup steps
1) Install plugins in your active environment: `pip install pytest-rerunfailures` (optional: `pytest-testmon`).
2) Keep using your existing `browserstack.yml` (platforms, logs). Pass pytest flags after `pytest` in the `browserstack-sdk` command.

## Optional SDK logging to aid flakiness triage
- In `browserstack.yml`, set: `debug: true`, `networkLogs: true`, `consoleLogs: info`.

## If you do have ITO enabled
- Use the ITO/Observability YAML as documented for your language version. Key names like `testOrchestrationOptions` may live in a different config than this repo’s sample `browserstack.yml`.
- Confirm placement and supported keys in your BrowserStack account docs, then add them to the correct file. Mixing ITO keys into this simple SDK YAML will not have effect.

