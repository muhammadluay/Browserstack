import os
from selenium.webdriver.support.ui import WebDriverWait


def test_swagger_ui_loads(driver):
    base_url = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")
    driver.get(base_url + "/swagger")

    WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
    body = (driver.page_source or "").lower()
    assert "browserstack demo api" in body or "swagger" in body, "Swagger UI should render"

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Swagger UI visible"}}'
    )

