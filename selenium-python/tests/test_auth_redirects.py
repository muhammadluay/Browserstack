import os
from urllib.parse import urlparse, parse_qs

import pytest
from selenium.webdriver.support.ui import WebDriverWait


USE_SDK = os.getenv("USE_BSTACK_SDK", "").strip().lower() in {"1", "true", "yes", "on"}
if USE_SDK:
    # Let BrowserStack SDK drive the matrix defined in browserstack.yml
    MATRIX = [{}]
    MATRIX_IDS = ["sdk-platform"]
else:
    MATRIX = [
        {"browserName": "Chrome", "os": "Windows", "osVersion": "11"},
        {"browserName": "Firefox", "os": "Windows", "osVersion": "11"},
        {"browserName": "Edge", "os": "Windows", "osVersion": "11"},
    ]
    MATRIX_IDS = [
        "win11-chrome",
        "win11-firefox",
        "win11-edge",
    ]

PROTECTED = [
    ("/offers", "offers"),
    ("/orders", "orders"),
    ("/checkout", "checkout"),
    ("/favourites", "favourites"),
]


def _wait_redirected(driver, expect_param: str):
    def redirected(d):
        u = urlparse(d.current_url)
        if u.path != "/signin":
            return False
        q = parse_qs(u.query)
        return q.get(expect_param, ["false"])[0] == "true"

    WebDriverWait(driver, 20).until(redirected)


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
@pytest.mark.parametrize("path,flag", PROTECTED, ids=["offers", "orders", "checkout", "favourites"])
def test_redirects_when_not_logged_in(driver, path: str, flag: str):
    base = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")

    # Ensure clean state
    driver.get("about:blank")
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    driver.get(base + "/signin")
    try:
        driver.execute_script("sessionStorage.clear(); localStorage.clear();")
    except Exception:
        pass

    # Visit protected path and assert redirect to /signin?flag=true
    driver.get(base + path)
    _wait_redirected(driver, flag)

    # Mark session status for BrowserStack for clarity
    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Unauthenticated access to %s redirected to /signin?%s=true"}}' % (path, flag)
    )


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
@pytest.mark.parametrize("path,flag", PROTECTED, ids=["offers", "orders", "checkout", "favourites"])
def test_access_with_session_username(driver, path: str, flag: str):
    base = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")

    # Seed a username into sessionStorage to simulate logged-in state
    driver.get(base + "/signin")
    user = os.getenv("TEST_USER_DEMO", "demo_user")
    driver.execute_script("sessionStorage.setItem('username', arguments[0]);", user)

    # Now visit the protected page and assert we are NOT on /signin
    driver.get(base + path)

    def not_signin(d):
        return urlparse(d.current_url).path != "/signin"

    WebDriverWait(driver, 20).until(not_signin)

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Authenticated (sessionStorage) access to %s did not redirect to /signin"}}' % (path)
    )


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
@pytest.mark.parametrize("path", [p for p, _ in PROTECTED], ids=["offers", "orders", "checkout", "favourites"])
def test_access_with_session_username(driver, path: str):
    base = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")

    # Pre-set sessionStorage.username to simulate login
    driver.get(base + "/")
    driver.execute_script("sessionStorage.setItem('username','demo_user');")

    driver.get(base + path)
    WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
    assert "/signin" not in driver.current_url, f"Should not redirect to signin for {path} when username present"

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Access to %s allowed with sessionStorage.username"}}' % (path)
    )
