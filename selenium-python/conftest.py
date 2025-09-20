import os
import pytest
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver import ChromeOptions, FirefoxOptions
try:
    from selenium.webdriver import EdgeOptions, SafariOptions
except Exception:  # older seleniums may not expose these
    EdgeOptions = None
    SafariOptions = None


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)


def build_capabilities(test_name: str, overrides: dict | None = None) -> dict:
    username = os.getenv("BROWSERSTACK_USERNAME")
    access_key = os.getenv("BROWSERSTACK_ACCESS_KEY")
    if not username or not access_key:
        raise RuntimeError("BROWSERSTACK_USERNAME or BROWSERSTACK_ACCESS_KEY is not set. Add them to .env")

    browser_name = os.getenv("BROWSER_NAME", "Chrome")
    browser_version = os.getenv("BROWSER_VERSION", "latest")
    os_name = os.getenv("OS", "Windows")
    os_version = os.getenv("OS_VERSION", "11")

    bstack_opts: dict = {
        "os": os_name,
        "osVersion": os_version,
        "projectName": os.getenv("BROWSERSTACK_PROJECT_NAME", "Testathon Project"),
        "buildName": os.getenv("BROWSERSTACK_BUILD_NAME", "local-dev-build-1"),
        "sessionName": test_name,
        "seleniumVersion": "4.22.0",
        # Provide credentials in capabilities so both SDK and non-SDK runs authenticate
        "userName": username,
        "accessKey": access_key,
    }

    # Optional local testing
    if os.getenv("BROWSERSTACK_LOCAL", "false").lower() in ("1", "true", "yes"): 
        bstack_opts["local"] = "true"
        if os.getenv("BROWSERSTACK_LOCAL_IDENTIFIER"):
            bstack_opts["localIdentifier"] = os.getenv("BROWSERSTACK_LOCAL_IDENTIFIER")

    caps: dict = {
        "browserName": browser_name,
        "browserVersion": browser_version,
        "bstack:options": bstack_opts,
    }
    # Apply overrides if provided
    if overrides:
        for k, v in overrides.items():
            if k in ("browserName", "browserVersion"):
                caps[k] = v
            elif k in ("os", "osVersion", "projectName", "buildName", "sessionName", "seleniumVersion", "local", "localIdentifier"):
                bstack_opts[k] = v
            else:
                # allow arbitrary capabilities to be set
                if k == "bstack:options" and isinstance(v, dict):
                    bstack_opts.update(v)
                else:
                    caps[k] = v
    # If targeting real mobile devices, do not send desktop-only keys
    real_mobile = False
    try:
        real_mobile = bool(bstack_opts.get("deviceName")) or str(bstack_opts.get("realMobile", "")).lower() in ("1", "true", "yes")
    except Exception:
        real_mobile = False
    if real_mobile:
        # Remove desktop OS key which conflicts with real device caps
        bstack_opts.pop("os", None)
        # Real devices do not accept browserVersion at top-level
        caps.pop("browserVersion", None)
        # Prefer Appium on real devices; avoid desktop-only seleniumVersion
        bstack_opts.pop("seleniumVersion", None)
        if "appiumVersion" not in bstack_opts:
            bstack_opts["appiumVersion"] = os.getenv("APPIUM_VERSION", "2.0")
    return caps


def _options_for_browser(browser_name: str):
    name = (browser_name or "").lower()
    if name == "chrome":
        return ChromeOptions()
    if name == "firefox":
        return FirefoxOptions()
    if name in ("edge", "microsoftedge") and EdgeOptions is not None:
        return EdgeOptions()
    if name == "safari" and SafariOptions is not None:
        return SafariOptions()
    # default fallback
    return ChromeOptions()


@pytest.fixture
def driver(request):
    use_sdk = os.getenv("USE_BSTACK_SDK", "false").lower() in ("1", "true", "yes")

    if use_sdk:
        # Let the BrowserStack SDK own capabilities, credentials, and hub URL.
        # Provide a minimal Options object; the SDK plugin patches it per platform.
        browser_name = os.getenv("BROWSER_NAME", "Chrome")
        opts = _options_for_browser(browser_name)
        driver = webdriver.Remote(options=opts)
    else:
        # Support per-test overrides via indirect parametrization
        overrides = getattr(request, 'param', None)
        caps = build_capabilities(test_name=request.node.name, overrides=overrides if isinstance(overrides, dict) else None)
        opts = _options_for_browser(caps.get("browserName"))
        for k, v in caps.items():
            opts.set_capability(k, v)

        # Non-SDK path: use cloud hub and pass credentials via capabilities (no basic auth in URL)
        hub = "https://hub-cloud.browserstack.com/wd/hub"
        driver = webdriver.Remote(command_executor=hub, options=opts)

    yield driver

    driver.quit()
