"""Helpers that read product details from the OpenFoodFacts API."""

import requests

API_ROOT = "https://world.openfoodfacts.org"
# OpenFoodFacts rejects anonymous clients that do not identify themselves.
HEADERS = {"User-Agent": "FlaskInventory/1.0 (retail inventory project)"}


class OpenFoodFactsError(Exception):
    """Raised when the external API cannot be used."""


def fetch_by_barcode(barcode):
    """Return one normalized product, or None when the barcode is unknown."""
    barcode = str(barcode).strip()
    if not barcode:
        return None
    payload = _get_json(f"{API_ROOT}/api/v2/product/{barcode}.json")
    # status 1 means OpenFoodFacts found a product. status 0 means it did not.
    if payload.get("status") != 1 or not isinstance(payload.get("product"), dict):
        return None
    return normalize_product(payload["product"])


def search_by_name(name):
    """Return up to five normalized products that match a name search."""
    name = str(name).strip()
    if not name:
        return []
    payload = _get_json(
        f"{API_ROOT}/cgi/search.pl",
        params={
            "search_terms": name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
        },
    )
    products = payload.get("products") or []
    found = []
    for product in products:
        if isinstance(product, dict):
            found.append(normalize_product(product))
    return found


def normalize_product(product):
    """Copy the OpenFoodFacts fields this app keeps in the inventory array."""
    name = product.get("product_name") or product.get("product_name_en") or "Unknown product"
    barcode = product.get("code") or product.get("_id") or ""
    return {
        "barcode": str(barcode).strip(),
        "product_name": str(name).strip() or "Unknown product",
        "brands": str(product.get("brands") or "").strip(),
        "ingredients_text": str(product.get("ingredients_text") or "").strip(),
        "categories": str(product.get("categories") or "").strip(),
        "image_url": str(product.get("image_url") or product.get("image_front_url") or "").strip(),
    }


def _get_json(url, params=None):
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise OpenFoodFactsError(
            "OpenFoodFacts could not be reached. Check your connection and try again."
        ) from exc
