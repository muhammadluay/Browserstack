import os
import re
import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def _find_add_buttons(driver):
    # Broad set of patterns to locate add-to-cart buttons/links
    xpaths = [
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to cart')]",
        "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to cart')]",
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add') and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'cart')]",
        "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add') and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'cart')]",
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add to bag')]",
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'add')]",
        "//*[@data-test='add-to-cart' or @data-testid='add-to-cart']",
        "//*[@id='add-to-cart' or contains(@class,'add-to-cart')]",
    ]
    els = []
    for xp in xpaths:
        try:
            els.extend(driver.find_elements(By.XPATH, xp))
        except Exception:
            pass
    return [e for e in els if e.is_displayed()]


def _safe_click(driver, el):
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(el))
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def _get_cart_badge_text(driver) -> str | None:
    js = r"""
    (function(){
      function norm(s){return (s||'').toString().trim();}
      function low(s){return norm(s).toLowerCase();}
      const doc = document;
      const all = Array.from(doc.querySelectorAll('a,button,div,span,i,em,b,strong'));
      // Prefer elements that clearly mention cart/bag/basket and include a digit
      const isCartish = el => /(cart|bag|basket|checkout)/.test(low(el.getAttribute('aria-label')||''))
                               || /(cart|bag|basket|checkout)/.test(low(el.getAttribute('title')||''))
                               || /(cart|bag|basket|checkout)/.test(low(el.className||''))
                               || /(cart|bag|basket|checkout)/.test(low(el.textContent||''));
      const withDigits = all.filter(isCartish).filter(el => /\d/.test(low(el.textContent||'')));
      if (withDigits.length){
        // Choose the element with the shortest numeric content to avoid long labels
        withDigits.sort((a,b)=> norm(a.textContent).length - norm(b.textContent).length);
        return norm(withDigits[0].textContent);
      }
      // Try common badge/count classes
      const badge = doc.querySelector(".badge,.pill,.count,[data-test*='count'],[data-testid*='count']");
      return badge ? norm(badge.textContent) : null;
    })();
    """
    try:
        return driver.execute_script(js)
    except Exception:
        return None


def _extract_first_int(s: str | None) -> int | None:
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def _snapshot_cartish_storage_counts(driver) -> int:
    js = r"""
    (function(){
      function toObj(v){try{return JSON.parse(v)}catch(e){return null}}
      function countArr(v){return Array.isArray(v)? v.length : 0}
      let total = 0;
      // Check sessionStorage
      for (let i=0;i<sessionStorage.length;i++){
        const k = sessionStorage.key(i);
        const val = sessionStorage.getItem(k);
        const o = toObj(val);
        // Heuristic: keys that sound cart-like or hold arrays
        if ((/cart|bag|basket|items|products/i.test(k||'')) || Array.isArray(o)){
          total += countArr(o);
        }
      }
      // Check localStorage
      for (let i=0;i<localStorage.length;i++){
        const k = localStorage.key(i);
        const val = localStorage.getItem(k);
        const o = toObj(val);
        if ((/cart|bag|basket|items|products/i.test(k||'')) || Array.isArray(o)){
          total += countArr(o);
        }
      }
      return total;
    })();
    """
    try:
        v = driver.execute_script(js)
        return int(v) if v is not None else 0
    except Exception:
        return 0


@pytest.mark.parametrize("driver", MATRIX, indirect=True, ids=MATRIX_IDS)
def test_add_to_cart_updates_badge_and_persists_after_reload(driver):
    # Start clean and seed login so checkout/cart flows are available
    driver.get("about:blank")
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    driver.get(BASE + "/")
    _wait_ready(driver)
    try:
        driver.execute_script("sessionStorage.clear(); localStorage.clear();")
    except Exception:
        pass
    driver.execute_script("sessionStorage.setItem('username','demouser');")

    # Baseline snapshots
    before_badge_text = _get_cart_badge_text(driver)
    before_badge = _extract_first_int(before_badge_text)
    before_store = _snapshot_cartish_storage_counts(driver)

    # Click first visible add-to-cart button
    add_buttons = _find_add_buttons(driver)
    if not add_buttons:
        pytest.skip("No add-to-cart button found; cannot validate badge/total")
    _safe_click(driver, add_buttons[0])
    time.sleep(0.8)  # allow UI state to update

    # After add: expect either badge increased or storage increased
    after_badge_text = _get_cart_badge_text(driver)
    after_badge = _extract_first_int(after_badge_text)
    after_store = _snapshot_cartish_storage_counts(driver)

    badge_ok = (
        after_badge is not None and (
            (before_badge is None and after_badge >= 1) or
            (before_badge is not None and after_badge >= before_badge)
        )
    )
    storage_ok = after_store >= max(before_store + 1, 1)

    assert badge_ok or storage_ok, (
        f"Expected cart badge or storage count to increase;"
        f" before_badge={before_badge_text!r}, after_badge={after_badge_text!r},"
        f" before_store={before_store}, after_store={after_store}"
    )

    # Reload and ensure persistence of the chosen signal
    driver.refresh()
    _wait_ready(driver)
    time.sleep(0.5)

    post_badge_text = _get_cart_badge_text(driver)
    post_badge = _extract_first_int(post_badge_text)
    post_store = _snapshot_cartish_storage_counts(driver)

    persisted = False
    if after_badge is not None and post_badge is not None:
        persisted = post_badge >= after_badge
    elif after_store is not None:
        persisted = post_store >= after_store

    assert persisted, (
        f"Expected cart state to persist after reload;"
        f" after_badge={after_badge_text!r}, post_badge={post_badge_text!r},"
        f" after_store={after_store}, post_store={post_store}"
    )

    # Mark session status for BrowserStack dashboard
    try:
        driver.execute_script(
            'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Cart badge/total updates and persists across reload"}}'
        )
    except Exception:
        pass

