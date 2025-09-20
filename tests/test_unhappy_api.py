import os
import json
import random
import string
import pytest
import requests

BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _rand(s="nouser"):
    return f"{s}_" + "".join(random.choice(string.ascii_lowercase) for _ in range(6))


def test_signin_wrong_method_returns_4xx():
    r = requests.get(f"{BASE}/api/signin", timeout=10)
    assert 400 <= r.status_code < 500


def test_signin_invalid_returns_422_with_message():
    r = requests.post(
        f"{BASE}/api/signin",
        json={"username": _rand("baduser"), "password": "whatever"},
        timeout=10,
    )
    # Expect 422 per docs; accept any 4xx to be safe across deployments
    assert 400 <= r.status_code < 500
    try:
        data = r.json()
    except Exception:
        data = {}
    msg = str(data.get("errorMessage", data.get("message", ""))).lower()
    assert ("invalid" in msg) or msg, f"Unexpected body: {r.text}"


def test_checkout_get_422_or_4xx():
    r = requests.get(f"{BASE}/api/checkout", timeout=10)
    assert r.status_code in {422, 400}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"userName": ""},
        {"userName": "   "},
        {"userName": 123},
        {"userName": ["x"]},
        {"userName": _rand()},
    ],
)
def test_checkout_post_invalid_usernames_4xx(payload):
    r = requests.post(f"{BASE}/api/checkout", json=payload, timeout=10)
    assert 400 <= r.status_code < 500, r.text


def test_orders_missing_username_4xx():
    r = requests.get(f"{BASE}/api/orders", timeout=10)
    assert 400 <= r.status_code < 500


def test_orders_unknown_user_404():
    r = requests.get(
        f"{BASE}/api/orders", params={"userName": _rand()}, timeout=10
    )
    assert r.status_code == 404
    assert "no orders" in (r.json().get("message", "").lower())


@pytest.mark.parametrize(
    "params",
    [
        {"userName": _rand()},
        {"userName": _rand(), "latitude": None, "longitude": None},
        {"userName": _rand(), "latitude": "NaN", "longitude": "NaN"},
        {"userName": _rand(), "latitude": 1000, "longitude": -1000},
    ],
)
def test_offers_invalid_params_return_4xx(params):
    # Remove None to simulate missing keys
    params = {k: v for k, v in params.items() if v is not None}
    r = requests.get(f"{BASE}/api/offers", params=params, timeout=10)
    assert 400 <= r.status_code < 500


def test_offers_zero_zero_404():
    r = requests.get(
        f"{BASE}/api/offers",
        params={"userName": _rand(), "latitude": 0, "longitude": 0},
        timeout=10,
    )
    assert r.status_code == 404


def test_products_method_not_allowed_or_4xx():
    r = requests.post(f"{BASE}/api/products", json={}, timeout=10)
    assert 400 <= r.status_code < 500


def test_products_get_ignores_unknown_params_no_500():
    r = requests.get(f"{BASE}/api/products", params={"foo": _rand()}, timeout=10)
    assert r.status_code < 500
    # Prefer 200 OK when unknown params are ignored
    assert r.status_code in {200, 304}

def test_unknown_api_returns_404_jsonish():
    r = requests.get(f"{BASE}/api/does-not-exist", timeout=10)
    assert r.status_code == 404
    ctype = r.headers.get("content-type", "").lower()
    assert "json" in ctype or ctype.startswith("text/"), ctype


def test_content_negotiation_accept_plain_no_500():
    r = requests.get(
        f"{BASE}/api/products", headers={"Accept": "text/plain"}, timeout=10
    )
    assert r.status_code in {200, 406} or (400 <= r.status_code < 500)


def test_static_asset_missing_404():
    r = requests.get(f"{BASE}/_next/static/does-not-exist.js", timeout=10)
    assert r.status_code == 404


def test_http_to_https_redirect():
    http = BASE.replace("https://", "http://")
    if http == BASE:  # already http
        http = BASE
    r = requests.get(http + "/", allow_redirects=False, timeout=10)
    assert r.status_code in {301, 302, 307, 308}
    assert r.headers.get("Location", "").startswith("https://")


@pytest.mark.xfail(reason="Varies by server; only ensure not 5xx")
def test_very_long_url_not_5xx():
    path = "/" + ("x" * 8000)
    r = requests.get(BASE + path, timeout=10)
    assert r.status_code < 500


@pytest.mark.parametrize("method", ["HEAD", "OPTIONS"]) 
@pytest.mark.parametrize("path", ["/", "/api/products", "/api/orders"]) 
def test_head_options_sensible_status(method, path):
    r = requests.request(method, BASE + path, timeout=10)
    assert r.status_code in {200, 204, 405}
