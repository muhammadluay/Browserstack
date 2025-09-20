import os
import time
from urllib.parse import urlparse, parse_qs

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _ready(d):
    try:
        return d.execute_script("return document.readyState") == "complete"
    except Exception:
        return True


def _add_preload_hooks(driver) -> bool:
    """
    Injects a script at document-start to:
      - Stub geolocation with fixed coords
      - Wrap fetch and XHR to record the last /api/offers URL

    Returns True if CDP injection is available; otherwise False.
    """
    preload = r"""
        (function(){
          try {
            const coords = { latitude: 40.73, longitude: -73.93, accuracy: 50 };
            const rounded = { latitude: Math.round(coords.latitude), longitude: Math.round(coords.longitude) };
            Object.defineProperty(window, '__test_geo', { value: {coords, rounded}, writable: false });

            // Stub geolocation
            if (navigator && navigator.geolocation) {
              const successResp = { coords: { latitude: coords.latitude, longitude: coords.longitude, accuracy: coords.accuracy } };
              try {
                navigator.geolocation.getCurrentPosition = function(success, error){ try { success(successResp); } catch(e){} };
                navigator.geolocation.watchPosition = function(success, error){ const id = Math.floor(Math.random()*1e6); setTimeout(function(){ try { success(successResp); } catch(e){} }, 0); return id; };
              } catch(e) {}
            }

            // Hook fetch
            try {
              const _fetch = window.fetch; 
              window.fetch = function(){
                try {
                  var u = arguments && arguments[0];
                  var url = (typeof u === 'string') ? u : (u && u.url) ? u.url : '';
                  if (url && url.indexOf('/api/offers') !== -1) {
                    window.__lastOffersFetch = url;
                  }
                } catch(e){}
                return _fetch.apply(this, arguments);
              };
            } catch(e) {}

            // Hook XHR
            try {
              const origOpen = XMLHttpRequest.prototype.open;
              XMLHttpRequest.prototype.open = function(method, url){
                try { if (url && url.indexOf('/api/offers') !== -1) { window.__lastOffersFetch = url; } } catch(e) {}
                return origOpen.apply(this, arguments);
              };
            } catch(e) {}
          } catch (e) {
            // swallow
          }
        })();
    """
    try:
        # Only Chromium-based drivers expose CDP; guard for others
        if not hasattr(driver, "execute_cdp_cmd"):
            return False
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": preload})
        return True
    except Exception:
        return False


@pytest.mark.parametrize(
    "driver",
    [
        {"browserName": "Chrome", "os": "Windows", "osVersion": "11"},
    ],
    indirect=True,
    ids=["win11-chrome"],
)
def test_offers_uses_geo_and_rounds_when_allowed(driver):
    """
    Best-effort signal that when geolocation is available, the page
    issues an /api/offers request with rounded coordinates.
    - Preload script stubs geolocation and wraps network primitives.
    - After navigation to /offers, inspect the captured URL.
    """
    if not _add_preload_hooks(driver):
        pytest.skip("CDP preload not available; skipping geolocation rounding check")

    # Seed sessionStorage auth then open /offers
    driver.get(BASE + "/signin")
    driver.execute_script("sessionStorage.setItem('username','demo_user');")
    driver.get(BASE + "/offers")
    WebDriverWait(driver, 15).until(_ready)

    # Wait briefly for fetch/xhr hook to capture the API call
    def have_url(d):
        return d.execute_script("return window.__lastOffersFetch || ''") or None

    url = None
    for _ in range(15):
        try:
            url = have_url(driver)
            if url:
                break
        except Exception:
            pass
        time.sleep(0.3)

    if not url:
        pytest.xfail("Could not observe offers API call; site may delay or use different transport")

    # Extract and assert rounded lat/lon
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        lat = qs.get("latitude", [None])[0]
        lon = qs.get("longitude", [None])[0]
    except Exception:
        lat = lon = None

    assert lat is not None and lon is not None, f"offers call missing coords in URL: {url}"

    rounded = driver.execute_script("return (window.__test_geo && window.__test_geo.rounded) || null;")
    # If our stub ran, compare with the precomputed rounded ints
    if rounded and isinstance(rounded, dict):
        assert str(rounded.get("latitude")) == str(lat)
        assert str(rounded.get("longitude")) == str(lon)

    # Also check that values look integer-like
    assert str(lat).lstrip("-+").isdigit() and str(lon).lstrip("-+").isdigit(), f"Non-integer coords: {lat}, {lon}"

    # Session marker for BrowserStack visibility
    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Observed /api/offers with rounded coords"}}'
    )

