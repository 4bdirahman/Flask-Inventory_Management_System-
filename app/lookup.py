"""Routes that read OpenFoodFacts and, when asked, copy a product into inventory."""

from flask import Blueprint, jsonify, request

from app.openfoodfacts import OpenFoodFactsError, fetch_by_barcode, search_by_name
from app.storage import InventoryError, add_item

lookup_bp = Blueprint("lookup", __name__)


@lookup_bp.get("/lookup/barcode/<barcode>")
def lookup_barcode(barcode):
    # Triggered by CLI "Find product" when the user searches with a barcode.
    # Does not change the inventory array.
    try:
        product = fetch_by_barcode(barcode)
    except OpenFoodFactsError as exc:
        return jsonify({"error": str(exc)}), 502
    if product is None:
        return jsonify({"error": "No product found for that barcode"}), 404
    return jsonify(product)


@lookup_bp.get("/lookup/name")
def lookup_name():
    # Triggered by CLI "Find product" when the user searches with a name.
    # Does not change the inventory array.
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Query parameter 'name' is required"}), 400
    try:
        products = search_by_name(name)
    except OpenFoodFactsError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"count": len(products), "products": products})


@lookup_bp.post("/inventory/import")
def import_product():
    # Triggered by CLI "Import from OpenFoodFacts" and `python cli.py import`.
    # Reads the external product, then appends it to the inventory array.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be JSON"}), 400

    barcode = str(data.get("barcode") or "").strip()
    name = str(data.get("name") or "").strip()
    if bool(barcode) == bool(name):
        return jsonify({"error": "Provide either a barcode or a name"}), 400

    try:
        if barcode:
            product = fetch_by_barcode(barcode)
            if product is None:
                return jsonify({"error": "No product found for that barcode"}), 404
        else:
            matches = search_by_name(name)
            if not matches:
                return jsonify({"error": "No product found for that name"}), 404
            product = matches[0]
    except OpenFoodFactsError as exc:
        return jsonify({"error": str(exc)}), 502

    payload = dict(product)
    payload["price"] = data.get("price")
    payload["quantity"] = data.get("quantity")
    try:
        item = add_item(payload)
    except InventoryError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(item), 201
