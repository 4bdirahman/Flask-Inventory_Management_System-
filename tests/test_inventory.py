def test_seed_items_have_ids(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 3
    ids = [item["id"] for item in body["inventory"]]
    assert ids == [1, 2, 3]
    assert body["inventory"][0]["product_name"] == "Organic Almond Milk"


def test_get_one_item(client):
    response = client.get("/inventory/2")
    assert response.status_code == 200
    item = response.get_json()
    assert item["id"] == 2
    assert item["brands"] == "General Mills"
    assert "ingredients_text" in item


def test_get_missing_item(client):
    response = client.get("/inventory/99")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Item not found"


def test_create_item(client):
    response = client.post(
        "/inventory",
        json={
            "product_name": "Oat Milk",
            "brands": "Oatly",
            "barcode": "1234567890123",
            "ingredients_text": "Oat base, water",
            "price": 4.5,
            "quantity": 10,
        },
    )
    assert response.status_code == 201
    created = response.get_json()
    assert created["id"] == 4
    assert created["product_name"] == "Oat Milk"
    assert created["price"] == 4.5
    assert created["quantity"] == 10

    stored = client.get("/inventory/4")
    assert stored.status_code == 200
    assert stored.get_json()["brands"] == "Oatly"


def test_create_item_rejects_missing_fields(client):
    response = client.post("/inventory", json={"product_name": "Only a name"})
    assert response.status_code == 400
    assert "price" in response.get_json()["error"]


def test_create_item_rejects_bad_price_and_quantity(client):
    bad_price = client.post(
        "/inventory",
        json={"product_name": "Crackers", "price": -1, "quantity": 2},
    )
    assert bad_price.status_code == 400

    bad_quantity = client.post(
        "/inventory",
        json={"product_name": "Crackers", "price": 1.5, "quantity": 1.5},
    )
    assert bad_quantity.status_code == 400


def test_create_item_rejects_non_json(client):
    response = client.post("/inventory", data="nope", content_type="text/plain")
    assert response.status_code == 400


def test_patch_price_and_quantity(client):
    response = client.patch("/inventory/1", json={"price": 3.99, "quantity": 20})
    assert response.status_code == 200
    item = response.get_json()
    assert item["price"] == 3.99
    assert item["quantity"] == 20
    assert item["product_name"] == "Organic Almond Milk"

    # The array itself changed, not just the response.
    listed = client.get("/inventory/1").get_json()
    assert listed["quantity"] == 20


def test_patch_missing_item(client):
    response = client.patch("/inventory/50", json={"price": 1})
    assert response.status_code == 404


def test_patch_rejects_unknown_field(client):
    response = client.patch("/inventory/1", json={"sku": "ABC"})
    assert response.status_code == 400
    assert "Unknown fields" in response.get_json()["error"]


def test_patch_rejects_empty_body(client):
    response = client.patch("/inventory/1", json={})
    assert response.status_code == 400


def test_delete_item(client):
    response = client.delete("/inventory/3")
    assert response.status_code == 200
    assert response.get_json()["id"] == 3

    missing = client.get("/inventory/3")
    assert missing.status_code == 404

    remaining = client.get("/inventory").get_json()
    assert remaining["count"] == 2
    assert all(item["id"] != 3 for item in remaining["inventory"])


def test_delete_missing_item(client):
    response = client.delete("/inventory/42")
    assert response.status_code == 404
