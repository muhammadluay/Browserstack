import os
import pytest
from selenium.webdriver.support.ui import WebDriverWait


USE_SDK = os.getenv("USE_BSTACK_SDK", "").strip().lower() in {"1", "true", "yes", "on"}
if USE_SDK:
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


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
def test_checkout_redirects_home_when_cart_empty(driver):
    base = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")

    # Simulate logged-in user but with empty cart
    driver.get(base + "/")
    driver.execute_script("sessionStorage.setItem('username','demo_user'); sessionStorage.removeItem('confirmationProducts'); sessionStorage.removeItem('confirmationTotal');")

    driver.get(base + "/checkout")
    WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
    # Expect redirect to home when cart is empty
    assert driver.current_url.rstrip("/") == base, f"Expected redirect to home, got {driver.current_url}"

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Empty cart redirected to home"}}'
    )

