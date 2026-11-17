"""CRUD routes for inventory items stored in the local array."""

from flask import Blueprint, jsonify, request

from app.storage import InventoryError, add_item, delete_item, get_all, get_by_id, update_item

inventory_bp = Blueprint("inventory", __name__)


def _json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


@inventory_bp.get("/inventory")
def list_inventory():
    # Triggered by CLI option "View all items" and `python cli.py list`.
    items = get_all()
    return jsonify({"count": len(items), "inventory": items})


@inventory_bp.get("/inventory/<int:item_id>")
def get_inventory_item(item_id):
    # Triggered by CLI option "View one item" and `python cli.py view <id>`.
    item = get_by_id(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item)


@inventory_bp.post("/inventory")
def create_inventory_item():
    # Triggered by CLI option "Add item" and `python cli.py add`.
    # Adds a new record to the inventory array.
    data = _json_object()
    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400
    try:
        item = add_item(data)
    except InventoryError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(item), 201


@inventory_bp.patch("/inventory/<int:item_id>")
def patch_inventory_item(item_id):
    # Triggered by CLI option "Update price or stock" and `python cli.py update`.
    # Changes price, quantity, or other stored fields on one item.
    data = _json_object()
    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400
    try:
        item = update_item(item_id, data)
    except InventoryError as exc:
        return jsonify({"error": str(exc)}), 400
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item)


@inventory_bp.delete("/inventory/<int:item_id>")
def remove_inventory_item(item_id):
    # Triggered by CLI option "Delete item" and `python cli.py delete`.
    # Removes the matching record from the inventory array.
    deleted_id = delete_item(item_id)
    if deleted_id is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify({"message": "Item deleted", "id": deleted_id})
