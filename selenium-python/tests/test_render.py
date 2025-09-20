import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


MATRIX = [
    {"browserName": "Chrome", "os": "Windows", "osVersion": "11"},
    {"browserName": "Firefox", "os": "Windows", "osVersion": "11"},
    {"browserName": "Edge", "os": "Windows", "osVersion": "11"},
]


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=[
    "win11-chrome",
    "win11-firefox",
    "win11-edge",
])
def test_homepage_renders_key_elements(driver):
    url = os.getenv("TEST_URL", "https://testathon.live/")

    driver.get(url)

    # Wait for full ready state
    WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")

    # Basic visibility checks: page title and core containers
    title = driver.title or ""
    assert len(title) > 0, "Title should not be empty"

    # Next.js root should be present
    root = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#__next")))
    assert root is not None

    # Footer tag presence (exists in HTML shell)
    footer = driver.find_elements(By.TAG_NAME, "footer")
    assert footer, "Expected a footer element to be present"

    # Mark session status for BrowserStack dashboard
    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Homepage rendered with title, root, and footer"}}'
    )

