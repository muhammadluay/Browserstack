import os
import pytest
import requests


BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def test_favicon_svg_loads():
    r = requests.get(f"{BASE}/favicon.svg", timeout=10)
    assert r.status_code == 200, f"/favicon.svg expected 200, got {r.status_code}"
    ctype = r.headers.get("content-type", "").lower()
    assert "image/svg" in ctype or ctype.endswith("svg+xml"), ctype


@pytest.mark.parametrize("path_pair", [("/offers", "/offers/"), ("/favourites", "/favourites/")])
def test_trailing_slash_canonicalization_no_500(path_pair):
    a, b = path_pair
    r1 = requests.get(BASE + a, timeout=10, allow_redirects=True)
    r2 = requests.get(BASE + b, timeout=10, allow_redirects=True)
    assert r1.status_code < 500 and r2.status_code < 500

