import os
import random
import string
import requests


BASE_URL = os.getenv("TEST_URL", "https://testathon.live/").rstrip("/")


def _rand_user(prefix: str = "user") -> str:
    return f"{prefix}_" + "".join(random.choice(string.ascii_lowercase) for _ in range(6))


def test_products_fields():
    res = requests.get(f"{BASE_URL}/api/products", timeout=15)
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, dict) and "products" in data
    assert isinstance(data["products"], list) and len(data["products"]) > 0
    sample = data["products"][0]
    for key in ("id", "title", "price", "sku", "availableSizes"):
        assert key in sample, f"Missing field {key} in product"


def test_checkout_returns_422_for_now():
    # Both GET and POST currently return 422 on the live site
    res_get = requests.get(f"{BASE_URL}/api/checkout", timeout=15)
    assert res_get.status_code == 422, res_get.text

    payload = {"userName": os.getenv("TEST_USER_DEMO", _rand_user("demo"))}
    res_post = requests.post(f"{BASE_URL}/api/checkout", json=payload, timeout=15)
    assert res_post.status_code == 422, res_post.text


def test_orders_nonexistent_user_404():
    uname = _rand_user("nouser")
    res = requests.get(f"{BASE_URL}/api/orders", params={"userName": uname}, timeout=15)
    assert res.status_code == 404, res.text
    data = res.json()
    assert data.get("message", "").lower().startswith("no orders")


def test_offers_returns_404_when_none():
    # Use coordinates that should have no offers (0,0)
    params = {
        "userName": os.getenv("TEST_USER_DEMO", _rand_user("nouser")),
        "latitude": 0,
        "longitude": 0,
    }
    res = requests.get(f"{BASE_URL}/api/offers", params=params, timeout=15)
    assert res.status_code == 404, res.text
    data = res.json()
    assert "cityName" in data


def test_signin_invalid_username_422():
    res = requests.post(f"{BASE_URL}/api/signin", json={"username": _rand_user("nouser"), "password": "x"}, timeout=15)
    assert res.status_code == 422, res.text
    data = res.json()
    assert data.get("errorMessage", "").lower() == "invalid username"
