"""Command line client for the inventory API.

Run `python cli.py` for the menu, or pass a subcommand such as `list`.
The Flask server must already be running.
"""

import argparse
import os
import sys

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:5000"

MENU = """
Inventory manager
1. View all items
2. View one item
3. Add item
4. Update price or stock
5. Delete item
6. Find product on OpenFoodFacts
7. Import product from OpenFoodFacts
8. Quit
""".strip()


class ApiError(Exception):
    """Raised when the inventory API returns an error or cannot be reached."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    """Small wrapper around the Flask routes."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def list_items(self):
        return self._request("GET", "/inventory")

    def get_item(self, item_id):
        return self._request("GET", f"/inventory/{item_id}")

    def add_item(self, payload):
        return self._request("POST", "/inventory", json_body=payload)

    def update_item(self, item_id, payload):
        return self._request("PATCH", f"/inventory/{item_id}", json_body=payload)

    def delete_item(self, item_id):
        return self._request("DELETE", f"/inventory/{item_id}")

    def lookup_barcode(self, barcode):
        return self._request("GET", f"/lookup/barcode/{barcode}")

    def lookup_name(self, name):
        return self._request("GET", "/lookup/name", params={"name": name})

    def import_product(self, payload):
        return self._request("POST", "/inventory/import", json_body=payload)

    def _request(self, method, path, json_body=None, params=None):
        try:
            response = requests.request(
                method,
                self.base_url + path,
                json=json_body,
                params=params,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise ApiError(
                "Could not reach the inventory API. Start the Flask server and try again."
            ) from exc

        if response.status_code >= 400:
            message = "Request failed"
            try:
                body = response.json()
                message = body.get("error", message)
            except ValueError:
                pass
            raise ApiError(message, response.status_code)

        if not response.content:
            return None
        return response.json()


def format_item(item):
    brand = item.get("brands") or "Unknown brand"
    barcode = item.get("barcode") or "n/a"
    return (
        f"[{item['id']}] {item['product_name']} | {brand} | "
        f"${item['price']:.2f} | stock {item['quantity']} | barcode {barcode}"
    )


def print_inventory(items):
    if not items:
        print("Inventory is empty.")
        return
    for item in items:
        print(format_item(item))


def print_details(item):
    print(format_item(item))
    print(f"Categories: {item.get('categories') or 'n/a'}")
    print(f"Ingredients: {item.get('ingredients_text') or 'n/a'}")
    if item.get("image_url"):
        print(f"Image: {item['image_url']}")


def print_external_product(product):
    brand = product.get("brands") or "Unknown brand"
    barcode = product.get("barcode") or "n/a"
    print(f"{product.get('product_name')} | {brand} | barcode {barcode}")
    print(f"Categories: {product.get('categories') or 'n/a'}")
    print(f"Ingredients: {product.get('ingredients_text') or 'n/a'}")


def prompt_price():
    raw = input("Price: ").strip()
    try:
        price = float(raw)
    except ValueError:
        raise ValueError("Price must be a number.")
    if price < 0:
        raise ValueError("Price cannot be negative.")
    return price


def prompt_quantity():
    raw = input("Quantity: ").strip()
    if not raw.isdigit():
        raise ValueError("Quantity must be a whole number.")
    return int(raw)


def action_list(client):
    print_inventory(client.list_items()["inventory"])


def action_view(client):
    raw = input("Item id: ").strip()
    if not raw.isdigit():
        print("Item id must be a whole number.")
        return
    print_details(client.get_item(int(raw)))


def action_add(client):
    name = input("Product name: ").strip()
    if not name:
        print("Product name is required.")
        return
    brand = input("Brand (optional): ").strip()
    barcode = input("Barcode (optional): ").strip()
    ingredients = input("Ingredients (optional): ").strip()
    price = prompt_price()
    quantity = prompt_quantity()
    item = client.add_item(
        {
            "product_name": name,
            "brands": brand,
            "barcode": barcode,
            "ingredients_text": ingredients,
            "price": price,
            "quantity": quantity,
        }
    )
    print("Added:")
    print(format_item(item))


def action_update(client):
    raw = input("Item id: ").strip()
    if not raw.isdigit():
        print("Item id must be a whole number.")
        return
    print("Leave a field blank if you do not want to change it.")
    price_raw = input("New price: ").strip()
    quantity_raw = input("New quantity: ").strip()
    payload = {}
    if price_raw:
        try:
            payload["price"] = float(price_raw)
        except ValueError:
            print("Price must be a number.")
            return
        if payload["price"] < 0:
            print("Price cannot be negative.")
            return
    if quantity_raw:
        if not quantity_raw.isdigit():
            print("Quantity must be a whole number.")
            return
        payload["quantity"] = int(quantity_raw)
    if not payload:
        print("Nothing to update.")
        return
    item = client.update_item(int(raw), payload)
    print("Updated:")
    print(format_item(item))


def action_delete(client):
    raw = input("Item id: ").strip()
    if not raw.isdigit():
        print("Item id must be a whole number.")
        return
    confirm = input("Delete this item? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    result = client.delete_item(int(raw))
    print(result["message"] + f" (id {result['id']}).")


def action_find(client):
    mode = input("Search by barcode (b) or name (n): ").strip().lower()
    if mode == "b":
        barcode = input("Barcode: ").strip()
        if not barcode:
            print("Barcode is required.")
            return
        print_external_product(client.lookup_barcode(barcode))
        return
    if mode == "n":
        name = input("Product name: ").strip()
        if not name:
            print("Product name is required.")
            return
        products = client.lookup_name(name)["products"]
        if not products:
            print("No products matched that name.")
            return
        for index, product in enumerate(products, start=1):
            brand = product.get("brands") or "Unknown brand"
            barcode = product.get("barcode") or "no barcode"
            print(f"{index}. {product['product_name']} | {brand} | {barcode}")
        return
    print("Enter b or n.")


def action_import(client):
    mode = input("Import by barcode (b) or name (n): ").strip().lower()
    if mode == "b":
        barcode = input("Barcode: ").strip()
    elif mode == "n":
        name = input("Product name: ").strip()
        if not name:
            print("Product name is required.")
            return
        products = client.lookup_name(name)["products"]
        if not products:
            print("No products matched that name.")
            return
        for index, product in enumerate(products, start=1):
            brand = product.get("brands") or "Unknown brand"
            code = product.get("barcode") or "no barcode"
            print(f"{index}. {product['product_name']} | {brand} | {code}")
        pick = input("Number to import: ").strip()
        if not pick.isdigit() or not (1 <= int(pick) <= len(products)):
            print("That is not one of the listed numbers.")
            return
        barcode = products[int(pick) - 1].get("barcode") or ""
        if not barcode:
            print("That product has no barcode, so it cannot be imported.")
            return
    else:
        print("Enter b or n.")
        return

    if not barcode:
        print("Barcode is required.")
        return

    print_external_product(client.lookup_barcode(barcode))
    confirm = input("Add this product to inventory? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    price = prompt_price()
    quantity = prompt_quantity()
    item = client.import_product({"barcode": barcode, "price": price, "quantity": quantity})
    print("Saved:")
    print(format_item(item))


def run_menu(client):
    actions = {
        "1": action_list,
        "2": action_view,
        "3": action_add,
        "4": action_update,
        "5": action_delete,
        "6": action_find,
        "7": action_import,
    }
    while True:
        print(MENU)
        try:
            choice = input("Choose an option: ").strip()
        except EOFError:
            print()
            return 0
        if choice in ("8", "q", "quit"):
            print("Goodbye.")
            return 0
        action = actions.get(choice)
        if action is None:
            print("Please enter a number from 1 to 8.")
            continue
        try:
            action(client)
        except (ApiError, ValueError) as exc:
            print(f"Error: {exc}")


def cmd_list(client, args):
    action_list(client)


def cmd_view(client, args):
    print_details(client.get_item(args.id))


def cmd_add(client, args):
    item = client.add_item(
        {
            "product_name": args.name,
            "brands": args.brand,
            "barcode": args.barcode,
            "ingredients_text": args.ingredients,
            "price": args.price,
            "quantity": args.quantity,
        }
    )
    print("Added:")
    print(format_item(item))


def cmd_update(client, args):
    payload = {}
    if args.price is not None:
        payload["price"] = args.price
    if args.quantity is not None:
        payload["quantity"] = args.quantity
    if not payload:
        raise ValueError("Provide --price, --quantity, or both.")
    item = client.update_item(args.id, payload)
    print("Updated:")
    print(format_item(item))


def cmd_delete(client, args):
    result = client.delete_item(args.id)
    print(result["message"] + f" (id {result['id']}).")


def cmd_find(client, args):
    if args.barcode:
        print_external_product(client.lookup_barcode(args.barcode))
        return
    products = client.lookup_name(args.name)["products"]
    if not products:
        print("No products matched that name.")
        return
    for index, product in enumerate(products, start=1):
        brand = product.get("brands") or "Unknown brand"
        barcode = product.get("barcode") or "no barcode"
        print(f"{index}. {product['product_name']} | {brand} | {barcode}")


def cmd_import(client, args):
    payload = {"price": args.price, "quantity": args.quantity}
    if args.barcode:
        payload["barcode"] = args.barcode
    else:
        payload["name"] = args.name
    item = client.import_product(payload)
    print("Saved:")
    print(format_item(item))


def build_parser():
    parser = argparse.ArgumentParser(description="Talk to the inventory API")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="Show every inventory item").set_defaults(func=cmd_list)

    view = sub.add_parser("view", help="Show one item")
    view.add_argument("id", type=int)
    view.set_defaults(func=cmd_view)

    add = sub.add_parser("add", help="Add an item by hand")
    add.add_argument("--name", required=True)
    add.add_argument("--price", required=True, type=float)
    add.add_argument("--quantity", required=True, type=int)
    add.add_argument("--brand", default="")
    add.add_argument("--barcode", default="")
    add.add_argument("--ingredients", default="")
    add.set_defaults(func=cmd_add)

    update = sub.add_parser("update", help="Change a price or stock level")
    update.add_argument("id", type=int)
    update.add_argument("--price", type=float)
    update.add_argument("--quantity", type=int)
    update.set_defaults(func=cmd_update)

    delete = sub.add_parser("delete", help="Remove an item")
    delete.add_argument("id", type=int)
    delete.set_defaults(func=cmd_delete)

    find = sub.add_parser("find", help="Look up a product on OpenFoodFacts")
    find_by = find.add_mutually_exclusive_group(required=True)
    find_by.add_argument("--barcode")
    find_by.add_argument("--name")
    find.set_defaults(func=cmd_find)

    bring_in = sub.add_parser("import", help="Copy an OpenFoodFacts product into inventory")
    bring_by = bring_in.add_mutually_exclusive_group(required=True)
    bring_by.add_argument("--barcode")
    bring_by.add_argument("--name")
    bring_in.add_argument("--price", required=True, type=float)
    bring_in.add_argument("--quantity", required=True, type=int)
    bring_in.set_defaults(func=cmd_import)

    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    base_url = os.environ.get("INVENTORY_API_URL", DEFAULT_BASE_URL)
    client = ApiClient(base_url)
    if not argv:
        return run_menu(client)

    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        args.func(client, args)
    except (ApiError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
