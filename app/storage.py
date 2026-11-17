"""Temporary inventory storage.

This list stands in for a database. Each product has an id so a route can
fetch, edit, or delete that one record. The product fields follow the shape
returned by OpenFoodFacts, with price and quantity added for the shop.
"""

import copy


class InventoryError(ValueError):
    """Raised when a create or update is rejected."""


# Sample stock shaped like trimmed OpenFoodFacts products.
SEED_ITEMS = [
    {
        "id": 1,
        "barcode": "0041220576924",
        "product_name": "Organic Almond Milk",
        "brands": "Silk",
        "ingredients_text": (
            "Filtered water, almonds, cane sugar, sea salt, locust bean gum, "
            "sunflower lecithin, gellan gum, natural flavor."
        ),
        "categories": "Plant-based foods, Beverages, Plant milks",
        "image_url": "",
        "price": 3.49,
        "quantity": 24,
    },
    {
        "id": 2,
        "barcode": "0012000016547",
        "product_name": "Honey Nut Cheerios",
        "brands": "General Mills",
        "ingredients_text": "Whole grain oats, sugar, oat bran, honey, corn starch, salt.",
        "categories": "Breakfasts, Cereals",
        "image_url": "",
        "price": 4.29,
        "quantity": 15,
    },
    {
        "id": 3,
        "barcode": "0038000840325",
        "product_name": "Canned Black Beans",
        "brands": "Goya",
        "ingredients_text": "Black beans, water, salt, calcium chloride.",
        "categories": "Canned foods, Legumes",
        "image_url": "",
        "price": 1.19,
        "quantity": 40,
    },
]

_items = []
_next_id = 1


def reset_inventory():
    """Restore the sample products. Tests call this before each case."""
    global _items, _next_id
    _items = copy.deepcopy(SEED_ITEMS)
    _next_id = max(item["id"] for item in _items) + 1


def get_all():
    return [copy.deepcopy(item) for item in _items]


def get_by_id(item_id):
    for item in _items:
        if item["id"] == item_id:
            return copy.deepcopy(item)
    return None


def add_item(data):
    """Append one product and assign the next id."""
    global _next_id
    if not isinstance(data, dict):
        raise InventoryError("Request body must be a JSON object")

    missing = []
    for field in ("product_name", "price", "quantity"):
        if field not in data or data[field] is None or data[field] == "":
            missing.append(field)
    if missing:
        raise InventoryError("Missing required fields: " + ", ".join(missing))

    item = {
        "id": _next_id,
        "barcode": _optional_text(data.get("barcode", "")),
        "product_name": _require_name(data.get("product_name")),
        "brands": _optional_text(data.get("brands", "")),
        "ingredients_text": _optional_text(data.get("ingredients_text", "")),
        "categories": _optional_text(data.get("categories", "")),
        "image_url": _optional_text(data.get("image_url", "")),
        "price": parse_price(data.get("price")),
        "quantity": parse_quantity(data.get("quantity")),
    }
    _items.append(item)
    _next_id += 1
    return copy.deepcopy(item)


def update_item(item_id, changes):
    """Change only the fields that were sent. Returns None if the id is missing."""
    if not isinstance(changes, dict):
        raise InventoryError("Request body must be a JSON object")

    allowed = {
        "barcode",
        "product_name",
        "brands",
        "ingredients_text",
        "categories",
        "image_url",
        "price",
        "quantity",
    }
    unknown = sorted(key for key in changes if key not in allowed)
    if unknown:
        raise InventoryError("Unknown fields: " + ", ".join(unknown))
    if not changes:
        raise InventoryError("No fields to update")

    for item in _items:
        if item["id"] != item_id:
            continue
        if "product_name" in changes:
            item["product_name"] = _require_name(changes["product_name"])
        if "barcode" in changes:
            item["barcode"] = _optional_text(changes["barcode"])
        if "brands" in changes:
            item["brands"] = _optional_text(changes["brands"])
        if "ingredients_text" in changes:
            item["ingredients_text"] = _optional_text(changes["ingredients_text"])
        if "categories" in changes:
            item["categories"] = _optional_text(changes["categories"])
        if "image_url" in changes:
            item["image_url"] = _optional_text(changes["image_url"])
        if "price" in changes:
            item["price"] = parse_price(changes["price"])
        if "quantity" in changes:
            item["quantity"] = parse_quantity(changes["quantity"])
        return copy.deepcopy(item)
    return None


def delete_item(item_id):
    for index, item in enumerate(_items):
        if item["id"] == item_id:
            _items.pop(index)
            return item_id
    return None


def parse_price(value):
    if isinstance(value, bool) or value is None:
        raise InventoryError("price must be a number")
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise InventoryError("price must be a number")
    if price < 0:
        raise InventoryError("price cannot be negative")
    return round(price, 2)


def parse_quantity(value):
    if isinstance(value, bool) or value is None:
        raise InventoryError("quantity must be a whole number")
    if isinstance(value, float):
        if not value.is_integer():
            raise InventoryError("quantity must be a whole number")
        value = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise InventoryError("quantity must be a whole number")
        value = int(text)
    elif not isinstance(value, int):
        raise InventoryError("quantity must be a whole number")
    if value < 0:
        raise InventoryError("quantity cannot be negative")
    return value


def _require_name(value):
    if not isinstance(value, str) or not value.strip():
        raise InventoryError("product_name is required")
    return value.strip()


def _optional_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise InventoryError("text fields must be strings")
    return value.strip()


reset_inventory()
