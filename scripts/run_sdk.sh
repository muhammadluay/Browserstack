#!/usr/bin/env bash
set -euo pipefail

# Load .env if present so BROWSERSTACK_USERNAME/ACCESS_KEY are exported
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export USE_BSTACK_SDK=1

# Default test path can be overridden by args
TEST_PATHS=("selenium-python/tests" "selenium-python/tests_api")
if [[ $# -gt 0 ]]; then
  TEST_PATHS=("$@")
fi

echo "Running via BrowserStack SDK across platforms from browserstack.yml"
echo "Tests: ${TEST_PATHS[*]}"

browserstack-sdk pytest -q "${TEST_PATHS[@]}"

