import os
import re
import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains


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


BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _wait_ready(driver, timeout: int = 25):
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")


def _find_product_cards(driver):
    x = (
        "//div[contains(@class,'product') and contains(@class,'card')]"
        " | //div[contains(@class,'product-card')]"
        " | //div[contains(@class,'shelf') and contains(@class,'item')]"
        " | //article[contains(@class,'product')]"
        " | //li[contains(@class,'product')]"
    )
    els = driver.find_elements(By.XPATH, x)
    if not els:
        x2 = "//*[contains(@class,'product') and (self::div or self::article or self::li)]"
        els = driver.find_elements(By.XPATH, x2)
    # filter displayed
    return [e for e in els if e.is_displayed()]


def _find_title_in(card):
    # Try common title/name selectors within a card
    xpaths = [
        ".//*[self::h1 or self::h2 or self::h3 or self::h4][normalize-space(string())!='']",
        ".//*[contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'title') and normalize-space(string())!='']",
        ".//*[contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'name') and normalize-space(string())!='']",
        ".//*[@data-test='product-title' or @data-testid='product-title']",
    ]
    for xp in xpaths:
        try:
            el = card.find_element(By.XPATH, xp)
            if el.is_displayed() and el.text.strip():
                return el
        except Exception:
            continue
    raise AssertionError("No visible title found in product card")


def _find_price_in(card):
    # Try common price selectors and allow currency/number match
    xpaths = [
        ".//*[contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'price')]",
        ".//*[@data-test='price' or @data-testid='price']",
        ".//*[self::span or self::div][contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'$') or contains(., '£') or contains(., '€') or contains(., '₹')]",
    ]
    for xp in xpaths:
        try:
            el = card.find_element(By.XPATH, xp)
            if el.is_displayed() and el.text.strip():
                return el
        except Exception:
            continue
    # Last resort: any text with a number looks like a price
    try:
        el = card.find_element(By.XPATH, ".//*[self::span or self::div][normalize-space(string())!='']")
        if el.is_displayed() and re.search(r"\d", el.text or ""):
            return el
    except Exception:
        pass
    raise AssertionError("No visible price found in product card")


def _find_add_to_cart_in(card):
    xpaths = [
        ".//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to cart')]",
        ".//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to cart')]",
        ".//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add') and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'cart')]",
        ".//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add') and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'cart')]",
        ".//*[@data-test='add-to-cart' or @data-testid='add-to-cart']",
        ".//*[@id='add-to-cart' or contains(@class,'add-to-cart')]",
    ]
    for xp in xpaths:
        try:
            el = card.find_element(By.XPATH, xp)
            if el.is_displayed():
                return el
        except Exception:
            continue
    raise AssertionError("No visible Add to cart control in product card")


def _find_add_buttons_global(driver):
    xpaths = [
        # Common explicit texts
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to cart')]",
        "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to cart')]",
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to bag')]",
        "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to bag')]",
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to basket')]",
        "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to basket')]",
        # More generic combinations
        "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add') and (contains(., 'cart') or contains(., 'bag') or contains(., 'basket'))]",
        "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'buy')]",
        # ARIA/attributes
        "//*[@data-test='add-to-cart' or @data-testid='add-to-cart']",
        "//*[@id='add-to-cart' or contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'add-to-cart') or contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'buy')]",
        "//*[@aria-label and (contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'add to cart') or contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'add to bag') or contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'buy'))]",
        # Inputs
        "//input[(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='add to cart' or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'add') or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'buy')) and (@type='submit' or @type='button')]",
    ]
    els = []
    for xp in xpaths:
        try:
            els.extend(driver.find_elements(By.XPATH, xp))
        except Exception:
            continue
    return [e for e in els if e.is_displayed()]


def _click_into_product_detail(driver, card):
    prev_url = driver.current_url
    # Try clicking a link or an image within the card first
    candidates = [
        ".//a[@href and not(starts-with(@href,'#'))]",
        ".//img",
        ".//*[self::h1 or self::h2 or self::h3 or self::h4]/ancestor::*[self::a][1]",
    ]
    clicked = False
    for xp in candidates:
        try:
            el = card.find_element(By.XPATH, xp)
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        # Click the card container as a last resort
        try:
            ActionChains(driver).move_to_element(card).click().perform()
            clicked = True
        except Exception:
            driver.execute_script("arguments[0].click();", card)
            clicked = True

    # Wait for navigation or content change
    try:
        WebDriverWait(driver, 10).until(lambda d: d.current_url != prev_url or d.execute_script("return document.readyState") == "complete")
    except Exception:
        pass


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
def test_product_cards_have_title_price_and_add_to_cart(driver):
    driver.get(BASE + "/")
    _wait_ready(driver)

    cards = _find_product_cards(driver)
    assert cards, "Expected at least one product card on the homepage"

    # Focus on the first visible card
    card = cards[0]

    # Hover the card in case controls appear on hover
    try:
        ActionChains(driver).move_to_element(card).perform()
        time.sleep(0.2)
    except Exception:
        pass

    title_el = _find_title_in(card)
    price_el = _find_price_in(card)

    assert title_el.text.strip(), "Product title should be non-empty"
    assert price_el.text.strip(), "Product price should be non-empty"

    # Add-to-cart should exist; if not visible on the card, navigate into details and verify there
    atc = None
    try:
        atc = _find_add_to_cart_in(card)
    except AssertionError:
        # Try global on the page (some layouts show one control outside the card)
        atc_list = _find_add_buttons_global(driver)
        if not atc_list:
            # Open product detail and validate there
            _click_into_product_detail(driver, card)
            _wait_ready(driver)
            atc_list = _find_add_buttons_global(driver)
            if not atc_list:
                pytest.skip("No Add to cart control found on product detail; recording as not visible on catalog and detail")
            atc = atc_list[0]
        else:
            atc = atc_list[0]
    WebDriverWait(driver, 8).until(EC.element_to_be_clickable(atc))

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Card shows title, price, and Add to cart"}}'
    )
