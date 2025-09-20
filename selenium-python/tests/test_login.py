import os
import pytest
from dotenv import load_dotenv

from selenium.webdriver.common.by import By

# Reuse the robust login helper
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from login_check import attempt_login  # type: ignore


# Ensure env is loaded when running pytest directly
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)


def _env_users():
    keys = [
        "TEST_USER_DEMO",
        "TEST_USER_IMAGE_NOT_LOADING",
        "TEST_USER_EXISTING_ORDER",
        "TEST_USER_FAV",
        "TEST_USER_LOCKED",
    ]
    users = [(k, os.getenv(k)) for k in keys]
    return [(k, v) for (k, v) in users if v]


USERS = _env_users()
if not USERS:
    pytest.skip("No TEST_USER_* variables configured in .env", allow_module_level=True)


@pytest.mark.parametrize("env_key, username", USERS)
def test_signin_flow(driver, env_key, username):
    base_url = os.getenv("TEST_URL", "https://testathon.live/")
    password = os.getenv("TEST_USER_PASSWORD", "testingisfun99")

    result = attempt_login(driver, base_url, username, password)

    # Define expectations: locked user is expected to fail, others succeed
    is_locked = env_key.endswith("_LOCKED") or username == os.getenv("TEST_USER_LOCKED", "locked_user")
    if is_locked:
        assert not result.ok, f"Locked user should fail, got: {result}"
    else:
        assert result.ok, f"Login should succeed for {username}: {result}"

    # Best-effort logout for succeeding sessions
    if result.ok:
        try:
            logout = driver.find_element(By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'logout')] | //button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'logout')]")
            logout.click()
        except Exception:
            pass
