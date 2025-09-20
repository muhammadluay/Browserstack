import os
import sys
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait


BASE = os.getenv('TEST_URL', 'https://testathon.live').rstrip('/')
PATHS = [
    ('/offers', 'offers'),
    ('/orders', 'orders'),
    ('/checkout', 'checkout'),
    ('/favourites', 'favourites'),
]


def build(headless: bool = True):
    opts = ChromeOptions()
    if headless:
        opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    return webdriver.Chrome(options=opts)


def assert_redirects(driver, path: str, expect_param: str):
    url = BASE + path
    driver.get('about:blank')
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    driver.get(BASE + '/signin')
    try:
        driver.execute_script('sessionStorage.clear(); localStorage.clear();')
    except Exception:
        pass
    driver.get(url)

    def redirected(d):
        u = urlparse(d.current_url)
        if u.path != '/signin':
            return False
        q = parse_qs(u.query)
        return q.get(expect_param, ['false'])[0] == 'true'

    WebDriverWait(driver, 20).until(redirected)
    print(f"[OK] {path} -> {driver.current_url}")


def main() -> int:
    headless = os.getenv('SHOW_BROWSER', '').strip().lower() not in {'1', 'true', 'yes', 'on'}
    d = build(headless=headless)
    try:
        for p, key in PATHS:
            assert_redirects(d, p, key)
        return 0
    finally:
        d.quit()


if __name__ == '__main__':
    sys.exit(main())

