import os
from urllib.parse import urlparse

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _ready(d):
    try:
        return d.execute_script("return document.readyState") == "complete"
    except Exception:
        return True


def _find_product_cards(driver):
    xp = (
        "//div[contains(@class,'product') and contains(@class,'card')]"
        " | //div[contains(@class,'product-card')]"
        " | //div[contains(@class,'shelf') and contains(@class,'item')]"
        " | //article[contains(@class,'product')]"
        " | //li[contains(@class,'product')]"
    )
    els = driver.find_elements(By.XPATH, xp)
    if not els:
        els = driver.find_elements(By.XPATH, "//*[contains(@class,'product')]")
    return els


def _find_fav_toggle_in(card):
    xpaths = [
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'fav')]",
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'heart')]",
        ".//*[self::button or self::a][contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'fav')]",
        ".//*[name()='svg']/ancestor::*[self::button or self::a][1]",
    ]
    for xp in xpaths:
        try:
            return card.find_element(By.XPATH, xp)
        except Exception:
            continue
    raise AssertionError("Could not locate favourite toggle within product card")


def _count_favourites(driver) -> int:
    driver.get(BASE + "/favourites")
    WebDriverWait(driver, 10).until(_ready)
    assert urlparse(driver.current_url).path == "/favourites"
    return len(_find_product_cards(driver))


@pytest.mark.parametrize(
    "driver",
    [
        {"browserName": "Chrome", "os": "Windows", "osVersion": "11"},
        {"browserName": "Firefox", "os": "Windows", "osVersion": "11"},
        {"browserName": "Edge", "os": "Windows", "osVersion": "11"},
    ],
    indirect=True,
    ids=["win11-chrome", "win11-firefox", "win11-edge"],
)
def test_favourite_toggle_persists_in_session(driver):
    # Login via sessionStorage flag
    driver.get(BASE + "/signin")
    driver.execute_script("sessionStorage.setItem('username','demo_user');")

    # Baseline favourites count
    initial = _count_favourites(driver)

    # Go home and add first product to favourites
    driver.get(BASE + "/")
    WebDriverWait(driver, 15).until(_ready)
    cards = _find_product_cards(driver)
    assert cards, "No product cards found on home"
    fav = _find_fav_toggle_in(cards[0])
    try:
        fav.click()
    except Exception:
        driver.execute_script("arguments[0].click();", fav)

    # Navigate to favourites and verify count increased or at least one present
    after = _count_favourites(driver)
    assert after >= max(1, initial), f"Expected favourites to persist in session (initial={initial}, after={after})"

    # Refresh and ensure persistence across reload
    driver.refresh()
    WebDriverWait(driver, 10).until(_ready)
    after_reload = len(_find_product_cards(driver))
    assert after_reload == after, "Favourites list should persist across reload in sessionStorage"

    # Optional: toggle back (best-effort) so repeated runs stay stable
    try:
        # Go home, un-favourite the same first product
        driver.get(BASE + "/")
        WebDriverWait(driver, 10).until(_ready)
        cards2 = _find_product_cards(driver)
        fav2 = _find_fav_toggle_in(cards2[0])
        driver.execute_script("arguments[0].click();", fav2)
    except Exception:
        pass

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Favourites toggle persisted in session"}}'
    )

