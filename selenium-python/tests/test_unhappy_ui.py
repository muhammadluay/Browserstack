import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")

# SDK/matrix wiring similar to other suites
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

# Mark as unhappy/ui
pytestmark = [pytest.mark.unhappy, pytest.mark.ui]


def _ready(d):
    return d.execute_script("return document.readyState") == "complete"


def _body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return (driver.page_source or "").lower()


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
def test_invalid_route_shows_404(driver):
    driver.get(BASE + "/this-path-should-not-exist-" + "x" * 8)
    WebDriverWait(driver, 10).until(_ready)
    text = _body_text(driver)
    assert "404" in text or "not found" in text


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
@pytest.mark.parametrize("path", ["/swagger/nope", "/openapi.json", "/swagger.json", "/robots.txt", "/sitemap.xml"])
def test_misc_404s(driver, path):
    driver.get(BASE + path)
    WebDriverWait(driver, 10).until(_ready)
    text = _body_text(driver)
    assert "404" in text or "not found" in text or "an unexpected error has occurred" in text


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
@pytest.mark.parametrize("path", ["/Offers", "/offers/", "//offers"]) 
def test_path_quirks_do_not_500(driver, path):
    driver.get(BASE + path)
    WebDriverWait(driver, 10).until(_ready)
    text = _body_text(driver)
    ok = ("/signin" in driver.current_url) or ("404" in text) or ("not found" in text)
    assert ok, f"Unexpected content for {path}: {driver.current_url}"


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
def test_confirmation_without_state_is_safe(driver):
    driver.get(BASE + "/")
    try:
        driver.execute_script("sessionStorage.clear(); localStorage.clear();")
    except Exception:
        pass
    driver.get(BASE + "/confirmation")
    WebDriverWait(driver, 10).until(_ready)
    text = _body_text(driver)
    assert "error" not in text or "an unexpected error has occurred" in text
