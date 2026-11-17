import requests

from app.openfoodfacts import OpenFoodFactsError, fetch_by_barcode, normalize_product, search_by_name


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


def test_normalize_product_keeps_expected_fields():
    product = normalize_product(
        {
            "code": "111",
            "product_name": "Sparkling Water",
            "brands": "Bubly",
            "ingredients_text": "Carbonated water, natural flavor",
            "categories": "Beverages",
            "image_front_url": "http://example.com/water.jpg",
        }
    )
    assert product == {
        "barcode": "111",
        "product_name": "Sparkling Water",
        "brands": "Bubly",
        "ingredients_text": "Carbonated water, natural flavor",
        "categories": "Beverages",
        "image_url": "http://example.com/water.jpg",
    }


def test_fetch_by_barcode_reads_product(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        assert url.endswith("/api/v2/product/111.json")
        assert "User-Agent" in headers
        return FakeResponse(
            {
                "status": 1,
                "product": {
                    "code": "111",
                    "product_name": "Sparkling Water",
                    "brands": "Bubly",
                    "ingredients_text": "Water",
                },
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)
    product = fetch_by_barcode("111")
    assert product["product_name"] == "Sparkling Water"
    assert product["barcode"] == "111"


def test_fetch_by_barcode_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse({"status": 0, "product": None}),
    )
    assert fetch_by_barcode("000") is None


def test_fetch_by_barcode_raises_when_api_is_down(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fake_get)
    try:
        fetch_by_barcode("111")
        assert False, "expected OpenFoodFactsError"
    except OpenFoodFactsError as exc:
        assert "OpenFoodFacts" in str(exc)


def test_search_by_name(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        assert "search.pl" in url
        assert params["search_terms"] == "almond milk"
        return FakeResponse(
            {
                "products": [
                    {"code": "222", "product_name": "Almond Milk", "brands": "Silk"},
                    {"code": "333", "product_name_en": "Almond Drink", "brands": "Store"},
                ]
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)
    products = search_by_name("almond milk")
    assert len(products) == 2
    assert products[1]["product_name"] == "Almond Drink"


def test_lookup_barcode_route(client, monkeypatch):
    monkeypatch.setattr(
        "app.lookup.fetch_by_barcode",
        lambda barcode: {
            "barcode": barcode,
            "product_name": "Imported Tea",
            "brands": "Taylors",
            "ingredients_text": "Tea",
            "categories": "Drinks",
            "image_url": "",
        },
    )
    response = client.get("/lookup/barcode/999")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Imported Tea"


def test_lookup_barcode_not_found(client, monkeypatch):
    monkeypatch.setattr("app.lookup.fetch_by_barcode", lambda barcode: None)
    response = client.get("/lookup/barcode/999")
    assert response.status_code == 404


def test_lookup_name_route(client, monkeypatch):
    monkeypatch.setattr(
        "app.lookup.search_by_name",
        lambda name: [
            {
                "barcode": "999",
                "product_name": name,
                "brands": "Test",
                "ingredients_text": "",
                "categories": "",
                "image_url": "",
            }
        ],
    )
    response = client.get("/lookup/name?name=yogurt")
    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 1
    assert body["products"][0]["product_name"] == "yogurt"


def test_lookup_name_requires_query(client):
    response = client.get("/lookup/name")
    assert response.status_code == 400


def test_import_barcode_adds_to_inventory(client, monkeypatch):
    monkeypatch.setattr(
        "app.lookup.fetch_by_barcode",
        lambda barcode: {
            "barcode": barcode,
            "product_name": "Imported Oats",
            "brands": "Quaker",
            "ingredients_text": "Oats",
            "categories": "Cereals",
            "image_url": "",
        },
    )
    response = client.post(
        "/inventory/import",
        json={"barcode": "555", "price": 2, "quantity": 3},
    )
    assert response.status_code == 201
    created = response.get_json()
    assert created["product_name"] == "Imported Oats"
    assert created["price"] == 2.0
    assert created["quantity"] == 3

    stored = client.get(f"/inventory/{created['id']}")
    assert stored.status_code == 200
    assert stored.get_json()["brands"] == "Quaker"


def test_import_name_uses_first_match(client, monkeypatch):
    monkeypatch.setattr(
        "app.lookup.search_by_name",
        lambda name: [
            {
                "barcode": "777",
                "product_name": "First Match",
                "brands": "A",
                "ingredients_text": "",
                "categories": "",
                "image_url": "",
            }
        ],
    )
    response = client.post(
        "/inventory/import",
        json={"name": "match", "price": 1.25, "quantity": 8},
    )
    assert response.status_code == 201
    assert response.get_json()["product_name"] == "First Match"


def test_import_requires_price(client, monkeypatch):
    monkeypatch.setattr(
        "app.lookup.fetch_by_barcode",
        lambda barcode: {
            "barcode": barcode,
            "product_name": "No Price",
            "brands": "",
            "ingredients_text": "",
            "categories": "",
            "image_url": "",
        },
    )
    response = client.post("/inventory/import", json={"barcode": "555"})
    assert response.status_code == 400


def test_import_rejects_both_barcode_and_name(client):
    response = client.post(
        "/inventory/import",
        json={"barcode": "1", "name": "Milk", "price": 1, "quantity": 1},
    )
    assert response.status_code == 400


def test_lookup_reports_api_failure(client, monkeypatch):
    def explode(barcode):
        raise OpenFoodFactsError("OpenFoodFacts could not be reached. Check your connection and try again.")

    monkeypatch.setattr("app.lookup.fetch_by_barcode", explode)
    response = client.get("/lookup/barcode/123")
    assert response.status_code == 502
    assert "OpenFoodFacts" in response.get_json()["error"]
