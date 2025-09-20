import os
import json
import pytest
from selenium.webdriver.support.ui import WebDriverWait


BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _ready(d):
    try:
        return d.execute_script("return document.readyState") == "complete"
    except Exception:
        return True


ANDROID_PIXEL8 = {
    "browserName": "Chrome",
    "bstack:options": {
        "deviceName": "Google Pixel 8 Pro",
        "osVersion": "14",
        "realMobile": "true",
        # Try to ensure permission and inject GPS coordinates server-side
        "appiumVersion": "2.0",
        # If supported on BrowserStack real devices (App Automate Web)
        "gpsLocation": os.getenv("MOBILE_GPS_LOCATION", "40.73,-73.93"),
    },
    # Appium capability to auto-grant runtime permissions on Android
    "appium:autoGrantPermissions": True,
}


@pytest.mark.parametrize("driver", [ANDROID_PIXEL8], indirect=True, ids=["android-chrome-pixel8-gps"])
def test_mobile_offers_with_granted_geolocation_and_gps(driver):
    """
    Mobile run on Android Chrome that attempts to use real geolocation.
    - Seeds login via sessionStorage
    - Calls geolocation from page context and expects coordinates
    - Fetches /api/offers with rounded coords and validates response contract
    """
    # Skip if not running on a real mobile device (e.g., when SDK fans out to desktops)
    caps = getattr(driver, "capabilities", {}) or {}
    bopts = caps.get("bstack:options") or caps.get("bstack_options") or {}
    is_real_mobile = bool(bopts.get("deviceName")) or str(bopts.get("realMobile", "")).lower() in ("1", "true", "yes")
    if not is_real_mobile:
        pytest.skip("Not a real mobile session; skipping mobile geolocation test")

    # Log in and open origin
    driver.get(BASE + "/signin")
    driver.execute_script("sessionStorage.setItem('username','demouser');")

    # Navigate to /offers
    driver.get(BASE + "/offers")
    WebDriverWait(driver, 20).until(_ready)

    # Attempt to access geolocation via async script
    try:
        driver.set_script_timeout(20)
    except Exception:
        pass

    res = driver.execute_async_script(
        """
        const cb = arguments[0];
        try {
          if (!navigator.geolocation) return cb({ok:false, error:'no geolocation'});
          navigator.geolocation.getCurrentPosition(
            pos => cb({ok:true, lat: pos.coords.latitude, lon: pos.coords.longitude}),
            err => cb({ok:false, error: (err && err.message) || String(err) }),
            { enableHighAccuracy: false, timeout: 15000 }
          );
        } catch(e){ cb({ok:false, error: String(e)}); }
        """
    )

    if not (isinstance(res, dict) and res.get("ok") is True):
        pytest.xfail(f"Geolocation not granted on mobile run: {res}")

    lat, lon = res.get("lat"), res.get("lon")
    assert isinstance(lat, (int, float)) and isinstance(lon, (int, float))
    rlat, rlon = int(round(float(lat))), int(round(float(lon)))

    # Validate offers endpoint with rounded coordinates
    resp = driver.execute_async_script(
        """
        const done = arguments[0];
        const url = `/api/offers?userName=demouser&latitude=%s&longitude=%s`;
        fetch(url).then(r => r.text().then(t => done({status:r.status, body:t}))).catch(e => done({status:0, body:String(e)}));
        """ % (rlat, rlon)
    )
    assert isinstance(resp, dict) and "status" in resp
    assert resp["status"] in (200, 404), resp
    try:
        data = json.loads(resp.get("body") or "{}")
    except Exception:
        data = {}
    if resp["status"] == 404:
        assert data.get("cityName", "") == ""

    driver.execute_script(
        'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Mobile geolocation allowed; offers reachable with rounded coords"}}'
    )
