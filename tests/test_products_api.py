import os
import random
import string
import pytest
import requests

BASE = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _rand(n=8):
    return "".join(random.choice(string.ascii_letters) for _ in range(n))


def _parse_products(resp):
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        return data["products"], data
    if isinstance(data, list):
        return data, {"products": data}
    # Unknown shape; return empty list with raw for debugging
    return [], data


def test_products_base_returns_products_json():
    r = requests.get(f"{BASE}/api/products", timeout=10)
    assert r.status_code == 200
    products, raw = _parse_products(r)
    assert isinstance(products, list)


@pytest.mark.parametrize(
    "params",
    [
        {"foo": _rand()},
        {"foo": _rand(), "bar": _rand()},
        {"q": _rand(24)},
        {"search": _rand(24)},
        {"limit": 10},
        {"offset": 0},
        {"priceMin": 0, "priceMax": 99999},
        {"sort": "price"},
        {"sort": "-price"},
        {"category": "mobile"},
        {"size": "XL"},
        {"brand": "somebrand"},
    ],
)
def test_products_unknown_or_varied_params_do_not_500(params):
    r = requests.get(f"{BASE}/api/products", params=params, timeout=10)
    assert r.status_code in {200, 304} or (400 <= r.status_code < 500)
    # Prefer 200 OK; parse if 200/304
    if r.status_code in {200, 304}:
        products, _ = _parse_products(r)
        assert isinstance(products, list)


@pytest.mark.parametrize(
    "params",
    [
        [("foo", "a"), ("foo", "b")],  # duplicate key
        {"foo": ["a", "b", "c"]},  # array value
        {"foo": ""},  # empty string
        {"foo": " " * 10},  # whitespace
        {"foo": _rand(1024)},  # very long value
        {"FOO": _rand(), "Bar": _rand()},  # case variations
        {"limit": -1},  # negative numbers
        {"offset": 1.23},  # float
        {"availableSizes": ["S", "M"]},
    ],
)
def test_products_param_edge_cases_no_5xx(params):
    r = requests.get(f"{BASE}/api/products", params=params, timeout=10)
    assert r.status_code < 500
    if r.status_code in {200, 304}:
        products, _ = _parse_products(r)
        assert isinstance(products, list)


@pytest.mark.parametrize("accept", [
    "application/json",
    "text/plain",
    "application/xml",
])
def test_products_content_negotiation_no_5xx(accept):
    r = requests.get(
        f"{BASE}/api/products",
        headers={"Accept": accept},
        timeout=10,
    )
    assert r.status_code < 500


@pytest.mark.parametrize("method", ["HEAD", "OPTIONS"]) 
def test_products_head_options_sensible_status(method):
    r = requests.request(method, f"{BASE}/api/products", timeout=10)
    assert r.status_code in {200, 204, 405}

