import requests

from cli import ApiClient, ApiError, main, run_menu


def sample_item(**overrides):
    item = {
        "id": 4,
        "barcode": "111",
        "product_name": "Test Soda",
        "brands": "Fizz",
        "ingredients_text": "Water",
        "categories": "Drinks",
        "image_url": "",
        "price": 2.5,
        "quantity": 6,
    }
    item.update(overrides)
    return item


def test_client_list_calls_inventory_route(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b"{}"

        def json(self):
            return {"count": 1, "inventory": [sample_item()]}

    def fake_request(method, url, json=None, params=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        return FakeResponse()

    monkeypatch.setattr(requests, "request", fake_request)
    body = ApiClient("http://127.0.0.1:5000").list_items()
    assert captured == {"method": "GET", "url": "http://127.0.0.1:5000/inventory"}
    assert body["inventory"][0]["product_name"] == "Test Soda"


def test_client_surfaces_api_error(monkeypatch):
    class FakeResponse:
        status_code = 404
        content = b"{}"

        def json(self):
            return {"error": "Item not found"}

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse())
    try:
        ApiClient("http://127.0.0.1:5000").get_item(9)
        assert False, "expected ApiError"
    except ApiError as exc:
        assert exc.status_code == 404
        assert "not found" in str(exc).lower()


def test_client_reports_connection_failure(monkeypatch):
    def fake_request(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "request", fake_request)
    try:
        ApiClient("http://127.0.0.1:5000").list_items()
        assert False, "expected ApiError"
    except ApiError as exc:
        assert "Flask" in str(exc)


def test_list_command_prints_items(monkeypatch, capsys):
    monkeypatch.setattr(
        ApiClient,
        "list_items",
        lambda self: {"count": 1, "inventory": [sample_item()]},
    )
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert "Test Soda" in output
    assert "$2.50" in output


def test_add_command_sends_payload(monkeypatch, capsys):
    seen = {}

    def fake_add(self, payload):
        seen["payload"] = payload
        return sample_item(product_name=payload["product_name"], price=payload["price"], quantity=payload["quantity"])

    monkeypatch.setattr(ApiClient, "add_item", fake_add)
    code = main(["add", "--name", "Test Soda", "--brand", "Fizz", "--price", "2.5", "--quantity", "6"])
    assert code == 0
    assert seen["payload"]["product_name"] == "Test Soda"
    assert seen["payload"]["price"] == 2.5
    assert seen["payload"]["quantity"] == 6
    assert "Added:" in capsys.readouterr().out


def test_update_command_requires_a_field(capsys):
    code = main(["update", "1"])
    assert code == 1
    assert "price" in capsys.readouterr().out.lower()


def test_update_command_patches_stock(monkeypatch, capsys):
    seen = {}

    def fake_update(self, item_id, payload):
        seen["id"] = item_id
        seen["payload"] = payload
        return sample_item(id=item_id, quantity=payload["quantity"])

    monkeypatch.setattr(ApiClient, "update_item", fake_update)
    assert main(["update", "1", "--quantity", "12"]) == 0
    assert seen == {"id": 1, "payload": {"quantity": 12}}
    assert "stock 12" in capsys.readouterr().out


def test_delete_command(monkeypatch, capsys):
    monkeypatch.setattr(ApiClient, "delete_item", lambda self, item_id: {"message": "Item deleted", "id": item_id})
    assert main(["delete", "3"]) == 0
    assert "Item deleted (id 3)." in capsys.readouterr().out


def test_find_command_by_name(monkeypatch, capsys):
    monkeypatch.setattr(
        ApiClient,
        "lookup_name",
        lambda self, name: {
            "count": 1,
            "products": [
                {
                    "barcode": "222",
                    "product_name": "Almond Milk",
                    "brands": "Silk",
                    "ingredients_text": "Almonds",
                    "categories": "Drinks",
                    "image_url": "",
                }
            ],
        },
    )
    assert main(["find", "--name", "almond milk"]) == 0
    assert "Almond Milk" in capsys.readouterr().out


def test_import_command_posts_barcode(monkeypatch, capsys):
    seen = {}

    def fake_import(self, payload):
        seen["payload"] = payload
        return sample_item()

    monkeypatch.setattr(ApiClient, "import_product", fake_import)
    assert main(["import", "--barcode", "111", "--price", "2.5", "--quantity", "6"]) == 0
    assert seen["payload"] == {"price": 2.5, "quantity": 6, "barcode": "111"}
    assert "Saved:" in capsys.readouterr().out


def test_menu_rejects_bad_choice_then_quits(monkeypatch, capsys):
    answers = iter(["0", "8"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert run_menu(ApiClient("http://127.0.0.1:5000")) == 0
    assert "number from 1 to 8" in capsys.readouterr().out


def test_menu_import_adds_product(monkeypatch, capsys):
    answers = iter(["7", "b", "111", "y", "2.50", "6", "8"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    class FakeClient:
        def lookup_barcode(self, barcode):
            assert barcode == "111"
            return {
                "barcode": "111",
                "product_name": "Test Soda",
                "brands": "Fizz",
                "ingredients_text": "Water",
                "categories": "Drinks",
                "image_url": "",
            }

        def import_product(self, body):
            assert body == {"barcode": "111", "price": 2.5, "quantity": 6}
            return sample_item()

    assert run_menu(FakeClient()) == 0
    output = capsys.readouterr().out
    assert "Saved:" in output
    assert "Test Soda" in output


def test_menu_shows_api_error(monkeypatch, capsys):
    answers = iter(["1", "8"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    class FakeClient:
        def list_items(self):
            raise ApiError("Could not reach the inventory API. Start the Flask server and try again.")

    assert run_menu(FakeClient()) == 0
    assert "Could not reach the inventory API" in capsys.readouterr().out


def test_command_failure_returns_nonzero(monkeypatch, capsys):
    def fake_request(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "request", fake_request)
    assert main(["list"]) == 1
    assert "Error:" in capsys.readouterr().out
